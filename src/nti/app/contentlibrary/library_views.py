#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for exposing the content library to clients.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from urllib import quote as UQ

from zope import component
from zope import interface

from zope.location.interfaces import ILocationInfo

from pyramid import traversal
from pyramid import httpexceptions as hexc
from pyramid.view import view_config, view_defaults

from nti.app.authentication import get_remote_user

from nti.app.renderers.interfaces import IPreRenderResponseCacheController
from nti.app.renderers.caching import AbstractReliableLastModifiedCacheController

from nti.appserver.dataserver_pyramid_views import _GenericGetView as GenericGetView

from nti.appserver.interfaces import ITopLevelContainerContextProvider

from nti.appserver.pyramid_authorization import is_readable

from nti.appserver.workspaces.interfaces import IService

from nti.common.maps import CaseInsensitiveDict

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IContentUnitHrefMapper

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IDataserverFolder

from nti.externalization.interfaces import LocatedExternalList

from nti.links.links import Link

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid

from . import LIBRARY_CONTAINER_PATH_GET_VIEW

PAGE_INFO_MT = nti_mimetype_with_class('pageinfo')
PAGE_INFO_MT_JSON = PAGE_INFO_MT + '+json'

def _encode(s):
	return s.encode('utf-8') if isinstance(s, unicode) else s

def find_page_info_view_helper( request, page_ntiid_or_content_unit ):
	"""
	Helper function to resolve a NTIID to PageInfo.
	"""

	# XXX Assuming one location in the hierarchy, plus assuming things
	# about the filename For the sake of the application (trello #932
	# https://trello.com/c/5cxwEgVH), if the question is nested in a
	# sub-section of a content library, we want to return the PageInfo
	# for the nearest containing *physical* file. In short, this means
	# we look for an href that does not have a '#' in it.
	if not IContentUnit.providedBy(page_ntiid_or_content_unit):
		content_unit = find_object_with_ntiid(page_ntiid_or_content_unit)
	else:
		content_unit = page_ntiid_or_content_unit

	while content_unit and '#' in getattr( content_unit, 'href', '' ):
		content_unit = getattr( content_unit, '__parent__', None )

	page_ntiid = ''
	if content_unit:
		page_ntiid = content_unit.ntiid
	elif isinstance(page_ntiid_or_content_unit, basestring):
		page_ntiid = page_ntiid_or_content_unit

	# Rather than redirecting to the canonical URL for the page, request it
	# directly. This saves a round trip, and is more compatible with broken clients that
	# don't follow redirects parts of the request should be native strings,
	# which under py2 are bytes. Also make sure we pass any params to subrequest
	path = b'/dataserver2/Objects/' + _encode(page_ntiid)
	if request.query_string:
		path += '?' + _encode(request.query_string)

	# set subrequest
	subrequest = request.blank( path )
	subrequest.method = b'GET'
	subrequest.possible_site_names = request.possible_site_names
	# prepare environ
	subrequest.environ[b'REMOTE_USER'] = request.environ['REMOTE_USER']
	subrequest.environ[b'repoze.who.identity'] = request.environ['repoze.who.identity'].copy()
	for k in request.environ:
		if k.startswith('paste.') or k.startswith('HTTP_'):
			if k not in subrequest.environ:
				subrequest.environ[k] = request.environ[k]
	subrequest.accept = PAGE_INFO_MT_JSON

	# invoke
	result = request.invoke_subrequest(subrequest)
	return result

def _create_page_info(request, href, ntiid, last_modified=0, jsonp_href=None):
	"""
	:param float last_modified: If greater than 0, the best known date for the
		modification time of the contents of the `href`.
	"""
	# Traverse down to the pages collection and use it to create the info.
	# This way we get the correct link structure

	remote_user = get_remote_user(request, dataserver=request.registry.getUtility(IDataserver))
	if not remote_user:
		raise hexc.HTTPForbidden()

	user_service = request.registry.getAdapter( remote_user, IService )
	user_workspace = user_service.user_workspace
	pages_collection = user_workspace.pages_collection
	info = pages_collection.make_info_for( ntiid )

	# set extra links
	if href:
		info.extra_links = (Link( href, rel='content' ),) # TODO: The rel?
	if jsonp_href:
		link = Link( jsonp_href, rel='jsonp_content', target_mime_type='application/json')
		info.extra_links = info.extra_links + (link,) # TODO: The rel?

	info.contentUnit = request.context
	if last_modified:
		# FIXME: Need to take into account the assessment item times as well
		# This is probably not huge, because right now they both change at the
		# same time due to the rendering process. But we can expect that to decouple
		# NOTE: The preferences decorator may change this, but only to be newer
		info.lastModified = last_modified
	return info

@view_config( name='' )
@view_config( name='pageinfo+json' )
@view_config( name='link+json' )
@view_defaults( route_name='objects.generic.traversal',
				renderer='rest',
				context='nti.contentlibrary.interfaces.IContentUnit',
				permission=nauth.ACT_READ,
				request_method='GET' )
class _LibraryTOCRedirectClassView(object):
	"""
	Given an :class:`lib_interfaces.IContentUnit`, redirect the
	request to the static content. This allows unifying handling of
	NTIIDs.

	If the client uses the ``Accept`` header to ask for a Link to the
	content, though, then return that link; the client will do the
	redirection manually. (This is helpful for clients that need to
	know the URL of the content and which are using libraries that
	otherwise would swallow it and automatically redirect.) Our response
	will include the ``Vary: Accept`` header.

	Certain browsers have a hard time dealing with the ``Vary:
	Accept`` header, and this is one place that it really matters. Our
	request provides an ETag that is variant-specific to encourage
	good behaviour. However, the browsers that apparently mis-behave,
	(Chrome [25,27)), pay no attention to that. They also pay no
	attention to Cache-Control: no-store, no-cache and Pragma:
	no-cache. We thus rely on the client to deal with this situation.
	To facilitate that, we are registered as the empty view name, plus
	two other view names; all of them use the standard Accept mechanism, but
	the alternate names allow browsers to form unique URLs (without the totally
	cache-busting use of query parameters).

	This also works when used as a view named for the ROOT ntiid; no
	href is possible, but the rest of the data can be returned.
	"""

	def __init__(self, request):
		self.request = request

	def _lastModified(self, request):
		# This should be the time of the .html file
		lastModified = request.context.lastModified
		# But the ToC is important too, so we take the newest
		# of all these that we can find
		root_package = traversal.find_interface(request.context, IContentPackage)
		lastModified = max( lastModified,
							getattr(root_package, 'lastModified', 0),
							getattr(root_package, 'index_last_modified', 0))
		return lastModified

	link_mt = nti_mimetype_with_class( 'link' )
	link_mt_json = link_mt + '+json'
	link_mts = (link_mt, link_mt_json)

	json_mt = 'application/json'
	page_info_mt = PAGE_INFO_MT
	page_info_mt_json = PAGE_INFO_MT_JSON
	page_mts = (json_mt,page_info_mt,page_info_mt_json)

	mts = ('text/html',link_mt,link_mt_json,json_mt,page_info_mt,page_info_mt_json)

	def _as_link(self, href, lastModified, request):
		link = Link( href, rel="content" )
		# We cannot render a raw link using the code in pyramid_renderers, but
		# we need to return one to get the right mime type header. So we
		# fake it by rendering here
		def _t_e_o(**kwargs):
			return {"Class": "Link",
					"MimeType": self.link_mt,
					"href": href,
					"rel": "content",
					'Last Modified': lastModified or None}

		link.toExternalObject = _t_e_o
		interface.alsoProvides(link, ILocationInfo)
		link.__parent__ = request.context
		link.__name__ = href
		link.getNearestSite = lambda: component.getUtility(IDataserver).root
		return link

	def __call__(self):
		request = self.request
		href = request.context.href
		jsonp_href = None

		# Right now, the ILibraryTOCEntries always have relative hrefs,
		# which may or may not include a leading /.
		assert not href.startswith( '/' ) or '://' not in href # Is it a relative path?

		# FIXME: We're assuming these map into the URL space
		# based in their root name. Is that valid? Do we need another mapping layer?
		href = IContentUnitHrefMapper(request.context).href or href
		jsonp_key = request.context.does_sibling_entry_exist(request.context.href + '.jsonp')
		if jsonp_key is not None and jsonp_key:
			jsonp_href = IContentUnitHrefMapper( jsonp_key ).href

		lastModified = self._lastModified( request )

		# If the client asks for a specific type of data,
		# a link, then give it to them. Otherwise...
		accept_type = 'text/html'
		if request.accept:
			accept_type = request.accept.best_match( self.mts )

		if accept_type in self.link_mts:
			return self._as_link( href, lastModified, request )

		if accept_type in self.page_mts:
			# Send back our canonical location, just in case we got here via
			# something like the _ContentUnitPreferencesPutView. This assists the cache
			# to know what to invalidate.
			# (Mostly in tests we find we cannot rely on traversal, so HACK it in manually)
			request.response.content_location = \
					UQ( ('/dataserver2/Objects/' + request.context.ntiid).encode( 'utf-8' ) )

			return _create_page_info(request,
									 href,
									 request.context.ntiid,
									 last_modified=lastModified, jsonp_href=jsonp_href)

		# ...send a 302. Return rather than raise so that webtest works better
		return hexc.HTTPSeeOther( location=href )

def _LibraryTOCRedirectView(request):
	return _LibraryTOCRedirectClassView( request )()

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  name=ROOT,
			  permission=nauth.ACT_READ,
			  request_method='GET' )
def _RootLibraryTOCRedirectView(request):
	"""
	For the root NTIID, we only support returning PageInfo (never a link to content,
	and never the content itself, because those things do not exist.) Thus we bypass
	the complex Accept logic of :class:`._LibraryTOCRedirectClassView`.
	"""
	# It turns out to be not worth it to try to share the logic
	# because our request.context is not specified (in practice, it may be a
	# _ContentUnitPreferences or _NTIIDsContainerResource)

	ntiid = request.view_name
	request.response.content_location = UQ(('/dataserver2/Objects/' + ntiid).encode('utf-8'))
	return _create_page_info(request, None, ntiid)

@view_config(context=IContentPackageLibrary,
			 request_method='GET' )
class MainLibraryGetView(GenericGetView):
	"Invoked to return the contents of a library."

	def __call__(self):
		# TODO: Should generic get view do this step?
		controller = IPreRenderResponseCacheController(self.request.context)
		controller( self.request.context, {'request': self.request } )
		# GenericGetView currently wants to try to turn the context into an ICollection
		# for externalization. We would like to be specific about that here, but
		# that causes problems when we try to find a CacheController for request.context
		#self.request.context = ICollection(self.request.context)
		return super(MainLibraryGetView,self).__call__()

@component.adapter(IContentPackageLibrary)
class _ContentPackageLibraryCacheController(AbstractReliableLastModifiedCacheController):

	# Before the advent of purchasables, there was no way the user
	# could modify his own library. Going through the purchase process
	# took a long time, so we had a 30 to 60 second max_age. Then
	# courses came along, and it was possible to enroll in a bunch of
	# them, one after the other, very quickly, and that max_age caused
	# the UI to not be able to see the new entries. This is unlikely
	# if you expect the user to actually consider what he's enrolling
	# in, but possible. And when it does happen, it's very confusing
	# to the end user and gives a very flaky impression.
	# So currently it is 0 for that use case.
	max_age = 0

	@property
	def _context_specific(self):
		return sorted( [x.ntiid for x in self.context.contentPackages] )

@view_config(context=IDataserverFolder,
			 name=LIBRARY_CONTAINER_PATH_GET_VIEW )
class LibraryPathView( GenericGetView ):
	"""
	Return an ordered list of lists of library paths to an object.
	Typically, we expect this to be called with the containerId
	of a UGD item.

	Typical return:
		[ [ <TopLevelContext>,
			<ContentPackage>,
			<PageInfo>* ],
			...
		]
	"""
	def _get_top_level_contexts( self, obj ):
		"Return a dict of ntiid to top_level_context."
		top_level_contexts = ITopLevelContainerContextProvider( obj, None )
		return top_level_contexts

	def _get_path_for_package(self, package, target_ntiid):
		"""
		"""
		def recur( unit ):
			item_ntiid = getattr( unit, 'ntiid', None )
			if item_ntiid == target_ntiid:
				return [ unit ]
			if target_ntiid in unit.embeddedContainerNTIIDs:
				item = find_object_with_ntiid( target_ntiid )
				return [ item, unit ]
			for child in unit.children:
				result = recur( child )
				if result:
					result.append( unit )
					return result

		results = recur( package )
		if results:
			results.reverse()
		return results

	def _externalize_children( self, units ):
		# For content units, we need to externalize as pageinfos.
		results = []
		try:
			for unit in units:
				try:
					unit_res = find_page_info_view_helper( self.request, unit )
					results.append( unit_res.json_body )
				except hexc.HTTPMethodNotAllowed:
					# Underlying content object, append as-is
					results.append( unit )
		except hexc.HTTPForbidden:
			# No permission
			pass
		return results

	def _get_legacy_path_to_id( self, container_id ):
		# In the worst case, we may have to go through the
		# library twice, looking for children and then
		# embedded. With caching, this may not be too horrible.
		library = component.queryUtility( IContentPackageLibrary )
		result = None
		if library:
			# This should hit most UGD on lessons.
			result = library.pathToNTIID( container_id )
			if not result:
				# Well, now we try embedded, and the first
				# of the results.
				result = library.pathsToEmbeddedNTIID()
				result = result[0] if result else result
		return result

	def _get_params(self):
		params = CaseInsensitiveDict(self.request.params)
		obj_ntiid = params.get( 'ObjectId' )
		if 	obj_ntiid is None or not is_valid_ntiid_string( obj_ntiid ):
			raise hexc.HTTPUnprocessableEntity( "Invalid ObjectId." )

		obj = find_object_with_ntiid( obj_ntiid )
		if obj is None:
			raise hexc.HTTPNotFound()
		return obj

	def __call__(self):
		result = LocatedExternalList()
		obj = self._get_params()
		# TODO We should make this work for multiple types.
		# TODO For instructors; that may not be true.  Do we get every
		# top context for a given container id?  Probably not, the
		# underlying adapter probably only picks one.  We probably
		# need an adapter that returns *every* possibility.
		# -- Or, we only care about either:
		#	1) A specific context (IContainerContext)
		#	2) Any possible context, which would be the first returned
		# 		by our underlying adapter.
		top_level_contexts = self._get_top_level_contexts( obj )
		container_id = obj.containerId
		# TODO We have some readings that do not exist in our catalog.
		# We need to fetch containers of content units.
		for top_level_context in top_level_contexts:
			# Bail if our top-level context is not readable.
			if not is_readable( top_level_context ):
				continue
			try:
				packages = top_level_context.ContentPackageBundle.ContentPackages
			except AttributeError:
				packages = (top_level_context.legacy_content_package,)
			for package in packages:
				path_list = self._get_path_for_package( package, container_id )
				if path_list:
					# We have a hit
					result_list = [ top_level_context ]
					if is_readable( package ):
						result_list.append( package )
						path_list = self._externalize_children( path_list )
						result_list.extend( path_list )
					result.append( result_list )

		# If we have nothing yet, it could mean our object
		# is in legacy content. So we have to look through the library.
		if not result and not top_level_contexts:
			legacy_path = self._get_legacy_path_to_id( container_id )
			if legacy_path:
				package = legacy_path[0]

				top_level_context = self._get_top_level_contexts( package )
				for top_level_context in top_level_contexts:
					# Bail if our top-level context is not readable.
					if not is_readable( top_level_context ):
						continue
					# We have a hit
					# Take the first we find
					result_list = [ top_level_context ]
					if is_readable( package ):
						result_list.append( package )
						if len( legacy_path ) > 1:
							path_list = legacy_path[1:]
							path_list = self._externalize_children( path_list )
							result_list.extend( path_list )
					result.append( result_list )
					break

		if not result:
			raise hexc.HTTPNotFound()
		return result
