#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for exposing the content library to clients.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from urllib import quote as UQ

from zope import interface
from zope import component

from zope.location import interfaces as loc_interfaces

from pyramid import traversal
from pyramid import httpexceptions as hexc
from pyramid.view import view_config, view_defaults

from nti.appserver import interfaces as app_interfaces
from nti.app.renderers import interfaces as app_renderers_interfaces
from nti.appserver.dataserver_pyramid_views import _GenericGetView as GenericGetView

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import users
from nti.dataserver import links
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.mimetype.mimetype import  nti_mimetype_with_class

from nti.ntiids import ntiids

PAGE_INFO_MT = nti_mimetype_with_class('pageinfo')
PAGE_INFO_MT_JSON = PAGE_INFO_MT + '+json'

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

	content_unit = ntiids.find_object_with_ntiid(page_ntiid_or_content_unit) \
				   if not lib_interfaces.IContentUnit.providedBy(page_ntiid_or_content_unit) else page_ntiid_or_content_unit
	while content_unit and '#' in getattr( content_unit, 'href', '' ):
		content_unit = getattr( content_unit, '__parent__', None )

	page_ntiid = ''
	if content_unit:
		page_ntiid = content_unit.ntiid
	elif isinstance(page_ntiid_or_content_unit, basestring):
		page_ntiid = page_ntiid_or_content_unit

	# Rather than redirecting to the canonical URL for the page, request it
	# directly. This saves a round trip, and is more compatible with broken clients that
	# don't follow redirects
	# parts of the request should be native strings, which under py2 are bytes
	path = b'/dataserver2/Objects/' + (page_ntiid.encode('utf-8') if isinstance(page_ntiid,unicode) else page_ntiid)
	subrequest = request.blank( path )
	subrequest.method = b'GET'
	subrequest.environ[b'REMOTE_USER'] = request.environ['REMOTE_USER']
	subrequest.environ[b'repoze.who.identity'] = request.environ['repoze.who.identity'].copy()
	subrequest.possible_site_names = request.possible_site_names
	for k in request.environ:
		if k.startswith('paste.') or k.startswith('HTTP_'):
			if k not in subrequest.environ:
				subrequest.environ[k] = request.environ[k]
	subrequest.accept = PAGE_INFO_MT_JSON
	return request.invoke_subrequest( subrequest )

def _create_page_info(request, href, ntiid, last_modified=0, jsonp_href=None):
	"""
	:param float last_modified: If greater than 0, the best known date for the
		modification time of the contents of the `href`.
	"""
	# Traverse down to the pages collection and use it to create the info.
	# This way we get the correct link structure

	remote_user = users.User.get_user(request.authenticated_userid,
									  dataserver=request.registry.getUtility(nti_interfaces.IDataserver))
	if not remote_user:
		raise hexc.HTTPForbidden()
	user_service = request.registry.getAdapter( remote_user, app_interfaces.IService )
	user_workspace = user_service.user_workspace
	pages_collection = user_workspace.pages_collection
	info = pages_collection.make_info_for( ntiid )
	if href:
		info.extra_links = (links.Link( href, rel='content' ),) # TODO: The rel?
	if jsonp_href:
		info.extra_links = info.extra_links + (links.Link( jsonp_href, rel='jsonp_content', target_mime_type='application/json' ),) # TODO: The rel?

	info.contentUnit = request.context

	if last_modified:
		# FIXME: Need to take into account the assessment item times as well
		# This is probably not huge, because right now they both change at the
		# same time due to the rendering process. But we can expect that to
		# decouple
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
		root_package = traversal.find_interface( request.context, lib_interfaces.IContentPackage )
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
		link = links.Link( href, rel="content" )
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
		interface.alsoProvides( link, loc_interfaces.ILocationInfo )
		link.__parent__ = request.context
		link.__name__ = href
		link.getNearestSite = lambda: component.getUtility( nti_interfaces.IDataserver ).root

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

		href = lib_interfaces.IContentUnitHrefMapper( request.context ).href or href

		jsonp_key = request.context.does_sibling_entry_exist( request.context.href + '.jsonp' )
		if jsonp_key is not None and jsonp_key:
			jsonp_href = lib_interfaces.IContentUnitHrefMapper( jsonp_key ).href

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
			# something like the _ContentUnitPreferencesPutView. This assists the cache to know
			# what to invalidate. (Mostly in tests we find we cannot rely on traversal, so HACK it in manually)
			request.response.content_location = UQ( ('/dataserver2/Objects/' + request.context.ntiid).encode( 'utf-8' ) )
			return _create_page_info(request, href, request.context.ntiid, last_modified=lastModified, jsonp_href=jsonp_href)

		# ...send a 302. Return rather than raise so that webtest works better
		return hexc.HTTPSeeOther( location=href )

def _LibraryTOCRedirectView(request):
	return _LibraryTOCRedirectClassView( request )()

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  name=ntiids.ROOT,
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
	request.response.content_location = UQ( ('/dataserver2/Objects/' + ntiid).encode( 'utf-8' ) )
	return _create_page_info(request, None, ntiid )


@view_config(
			  context=lib_interfaces.IContentPackageLibrary,
			  request_method='GET' )
class MainLibraryGetView(GenericGetView):
	"Invoked to return the contents of a library."

	def __call__(self):
		# TODO: Should generic get view do this step?
		controller = app_renderers_interfaces.IPreRenderResponseCacheController(self.request.context)
		controller( self.request.context, {'request': self.request } )
		# GenericGetView currently wants to try to turn the context into an ICollection
		# for externalization. We would like to be specific about that here, but
		# that causes problems when we try to find a CacheController for request.context
		#self.request.context = ICollection(self.request.context)
		return super(MainLibraryGetView,self).__call__()

from nti.app.renderers.caching import AbstractReliableLastModifiedCacheController
@component.adapter(lib_interfaces.IContentPackageLibrary)
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
