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

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.renderers.interfaces import IPreRenderResponseCacheController
from nti.app.renderers.caching import AbstractReliableLastModifiedCacheController

from nti.appserver.dataserver_pyramid_views import _GenericGetView as GenericGetView

from nti.appserver.interfaces import ITopLevelContainerContextProvider
from nti.appserver.interfaces import IHierarchicalContextProvider

from nti.appserver.pyramid_authorization import is_readable

from nti.appserver.workspaces.interfaces import IService

from nti.common.maps import CaseInsensitiveDict

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IContentUnitHrefMapper

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IHighlight
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import ITopic

from nti.externalization.interfaces import LocatedExternalList

from nti.links.links import Link

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid

from . import LIBRARY_PATH_GET_VIEW

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

def _get_wrapped_bundles( top_level_contexts ):
	results = []
	for top_level_context in top_level_contexts:
		try:
			results.append( top_level_context.ContentPackageBundle )
		except AttributeError:
			pass
	return results

def _dedupe_bundles( top_level_contexts ):
	"""
	Filter out bundles that may be contained by other contexts.
	"""
	results = []
	wrapped_bundles = _get_wrapped_bundles( top_level_contexts )
	for top_level_context in top_level_contexts:
		if top_level_context not in wrapped_bundles:
			results.append( top_level_context )
	return results

def _get_top_level_contexts( obj ):
	results = []
	for top_level_contexts in component.subscribers( (obj,),
													ITopLevelContainerContextProvider ):
		results.extend( top_level_contexts )
	return _dedupe_bundles( results )

def _get_top_level_contexts_for_user( obj, user ):
	results = []
	for top_level_contexts in component.subscribers( (obj, user),
													ITopLevelContainerContextProvider ):
		results.extend( top_level_contexts )
	return _dedupe_bundles( results )

def _get_wrapped_bundles_from_hierarchy( hierarchy_contexts ):
	"""
	For our hierarchy paths, get all contained bundles.
	"""
	top_level_contexts = (x[0] for x in hierarchy_contexts if x)
	return _get_wrapped_bundles( top_level_contexts )

def _dedupe_bundles_from_hierarchy( hierarchy_contexts ):
	"""
	Filter out bundles that may be contained by other contexts.
	"""
	results = []
	wrapped_bundles = _get_wrapped_bundles_from_hierarchy( hierarchy_contexts )
	for hierarchy_context in hierarchy_contexts:
		top_level_context = hierarchy_context[0]
		if top_level_context not in wrapped_bundles:
			results.append( hierarchy_context )
	return results

def _get_hierarchy_context( obj, user ):
	results = []
	for hiearchy_contexts in component.subscribers( (obj,user),
												IHierarchicalContextProvider ):
		results.extend( hiearchy_contexts )
	return _dedupe_bundles_from_hierarchy( results )

def _get_hierarchy_context_for_context( obj, top_level_context ):
	results = component.queryMultiAdapter(
									( top_level_context, obj ),
									IHierarchicalContextProvider )
	return results

def _get_board_obj_path( obj ):
	"""
	For a board level object, return the lineage path.
	"""
	# Permissioning concerns? If we have permission
	# on underlying object, we should have permission up the tree.
	result = LocatedExternalList()
	top_level_contexts = _get_top_level_contexts( obj )

	if top_level_contexts:
		def _top_level_endpoint( item ):
			return item is None or item in top_level_contexts
	else:
		# Blog, community boards, etc.
		def _top_level_endpoint( item ):
			return item is None \
				or IContentPackage.providedBy( item ) \
				or IEntity.providedBy( item )

	item = obj.__parent__
	result_list = [ item ]
	while not _top_level_endpoint( item ):
		item = item.__parent__
		if item is not None:
			result_list.append( item )

	result_list.reverse()
	result.append( result_list )
	return result

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=IDataserverFolder,
			  name=LIBRARY_PATH_GET_VIEW,
			  permission=nauth.ACT_READ,
			  request_method='GET' )
class _LibraryPathView( AbstractAuthenticatedView ):
	"""
	Return an ordered list of lists of library paths to an object.

	Typical return:
		[ [ <TopLevelContext>,
			<Heirarchical Node>,
			<Heirarchical Node>,
			<PageInfo>* ],
			...
		]
	"""
	def _get_path_for_package(self, package, target_ntiid):
		"""
		For a given package, return the path to the target ntiid.
		"""
		def recur( unit ):
			item_ntiid = getattr( unit, 'ntiid', None )
			if 		item_ntiid == target_ntiid \
				or target_ntiid in unit.embeddedContainerNTIIDs:
				return [ unit ]
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
			# The clients only need the leaf pageinfo. So
			# we start at the end.
			units.reverse()
			for unit in units:
				if IContentPackage.providedBy( unit ):
					continue
				try:
					unit_res = find_page_info_view_helper( self.request, unit )
					results.append( unit_res.json_body )
					break
				except hexc.HTTPMethodNotAllowed:
					# Underlying content object, append as-is
					results.append( unit )
		except hexc.HTTPForbidden:
			# No permission
			pass
		results.reverse()
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
				# Now we try embedded, and the first
				# of the results.
				result = library.pathsToEmbeddedNTIID( container_id )
				result = result[0] if result else result
		return result

	def _get_legacy_results( self, obj, target_ntiid ):
		"""
		We need to iterate through the library, and some paths
		only return the first available result. So we make
		sure we only return a single result for now.
		"""
		legacy_path = self._get_legacy_path_to_id( target_ntiid )
		if legacy_path:
			package = legacy_path[0]

			top_level_contexts = _get_top_level_contexts_for_user( package, self.remoteUser )
			for top_level_context in top_level_contexts:

				# Bail if our top-level context is not readable.
				if not is_readable( top_level_context ):
					continue
				# We have a hit.
				result_list = [ top_level_context ]
				if is_readable( package ):
					hierarchy_context = _get_hierarchy_context_for_context(
														obj, top_level_context )
					if len( hierarchy_context ) > 1:
						result_list.extend( hierarchy_context[1:] )
					path_list = self._externalize_children( legacy_path )
					result_list.extend( path_list )
				return result_list

	def _get_path(self, obj, target_ntiid):
		result = LocatedExternalList()

		hierarchy_contexts = _get_hierarchy_context( obj, self.remoteUser )
		# We have some readings that do not exist in our catalog.
		# We need content units to be indexed.
		for hierarchy_context in hierarchy_contexts:
			# Bail if our top-level context is not readable,
			# or if we're wrapped by another context.
			top_level_context = hierarchy_context[0]
			if not is_readable( top_level_context ):
				continue

			try:
				packages = top_level_context.ContentPackageBundle.ContentPackages
			except AttributeError:
				try:
					packages = (top_level_context.legacy_content_package,)
				except AttributeError:
					packages = top_level_context.ContentPackages

			for package in packages:
				path_list = self._get_path_for_package( package, target_ntiid )
				if path_list:
					# We have a hit
					result_list = [ top_level_context ]
					if is_readable( package ):
						# TODO permissions on nodes?
						if len( hierarchy_context ) > 1:
							result_list.extend( hierarchy_context[1:] )
						path_list = self._externalize_children( path_list )
						result_list.extend( path_list )
					result.append( result_list )

		# If we have nothing yet, it could mean our object
		# is in legacy content. So we have to look through the library.
		if not result and not hierarchy_contexts:
			logger.info( 'Iterating through library for library path.' )
			result_list = self._get_legacy_results( obj, target_ntiid )
			if result_list:
				result.append( result_list )

		# Not sure how we would cache here, it would have to be by user
		# since we may have user-specific data returned.
		return result

	def _sort(self, result_lists):
		"""
		Sorting by the length of the results may generally be good enough.
		Longer paths might indicate full permission down the path tree.
		"""
		result_lists.sort( key=lambda x: len( x ), reverse=True )

	def _get_params(self):
		params = CaseInsensitiveDict(self.request.params)
		obj_ntiid = params.get( 'objectId' )
		if 	obj_ntiid is None or not is_valid_ntiid_string( obj_ntiid ):
			raise hexc.HTTPUnprocessableEntity( "Invalid ObjectId." )

		obj = find_object_with_ntiid( obj_ntiid )
		# If we get a contained object, we need the path
		# to the container.
		if IHighlight.providedBy( obj ):
			obj_ntiid = obj.containerId
			obj = find_object_with_ntiid( obj_ntiid )
		if obj is None:
			raise hexc.HTTPNotFound( '%s not found' % obj_ntiid )

		# Get the ntiid off the object because we may have an OID
		obj_ntiid = getattr( obj, 'ntiid', None ) or obj_ntiid
		return obj, obj_ntiid

	def __call__(self):
		obj, object_ntiid = self._get_params()
		if ITopic.providedBy( obj ) or IPost.providedBy( obj ):
			results = _get_board_obj_path( obj )
		else:
			results = self._get_path( obj, object_ntiid )
			self._sort( results )
		return results

@view_config(context=IPost)
@view_config(context=ITopic)
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  name=LIBRARY_PATH_GET_VIEW,
			  permission=nauth.ACT_READ,
			  request_method='GET' )
class _PostLibraryPathView( AbstractAuthenticatedView ):
	"""
	For board items, getting the path traversal can
	be accomplished through lineage.
	"""

	def __call__(self):
		return _get_board_obj_path( self.context )
