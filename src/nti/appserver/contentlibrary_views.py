#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for exposing the content library to clients.

In addition to providing access to the content, this

$Id$
"""
from __future__ import print_function, unicode_literals

import persistent

import pyramid.security as sec
import pyramid.httpexceptions as hexc
from pyramid.threadlocal import get_current_request
from pyramid import traversal
from pyramid.view import view_config

from zope import interface
from zope import component
from zope.location import interfaces as loc_interfaces
from zope.annotation.factory import factory as an_factory

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import links
from nti.dataserver import containers
from nti.dataserver.mimetype import  nti_mimetype_with_class
from nti.dataserver import authorization as nauth
from nti.ntiids import ntiids

from nti.appserver import interfaces as app_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import to_external_object

def _create_page_info(request, href, ntiid, last_modified=0):
	"""
	:param float last_modified: If greater than 0, the best known date for the
		modification time of the contents of the `href`.
	"""
	# Traverse down to the pages collection and use it to create the info.
	# This way we get the correct link structure

	remote_user = users.User.get_user( sec.authenticated_userid( request ), dataserver=request.registry.getUtility(nti_interfaces.IDataserver) )
	user_service = request.registry.getAdapter( remote_user, app_interfaces.IService )
	user_workspace = user_service.user_workspace
	pages_collection = user_workspace.pages_collection
	info = pages_collection.make_info_for( ntiid )
	if href:
		info.extra_links = (links.Link( href, rel='content' ),) # TODO: The rel?

	info.contentUnit = request.context

	if last_modified:
		# FIXME: Need to take into account the assessment item times as well
		# This is probably not huge, because right now they both change at the
		# same time due to the rendering process. But we can expect that to
		# decouple
		info.lastModified = last_modified
	return info

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(app_interfaces.IContentUnitInfo)
class _ContentUnitAssessmentItemDecorator(object):

	def __init__( self, context ):
		self.context = context

	def decorateExternalMapping( self, context, result_map ):
		if context.contentUnit is None:
			return

		questions = component.getUtility( app_interfaces.IFileQuestionMap )
		for_file = questions.by_file.get( getattr( context.contentUnit, 'filename', None ) )
		if for_file:
			### XXX FIXME: We need to be sure we don't send back the
			# solutions and explanations right now
			result_map['AssessmentItems'] = to_external_object( for_file  )

@interface.implementer(app_interfaces.IContentUnitPreferences)
@component.adapter(containers.LastModifiedBTreeContainer)
class _ContentUnitPreferences(persistent.Persistent):

	__parent__ = None
	__name__ = None
	sharedWith = None

	def __init__( self ):
		pass

def _ContainerContentUnitPreferencesFactory(container):
	# TODO: If we move any of this, we'll need to remember to pass in the key=
	# argument otherwise we won't have access to the data that already exists
	return an_factory(_ContentUnitPreferences)(container)


@interface.implementer(ext_interfaces.IExternalMappingDecorator)
@component.adapter(app_interfaces.IContentUnitInfo)
class _ContentUnitPreferencesDecorator(object):

	def __init__( self, context ):
		self.context = context

	def decorateExternalMapping( self, context, result_map ):
		if context.contentUnit is None:
			return

		request = get_current_request()
		if not request: return
		remote_user = users.User.get_user( sec.authenticated_userid( request ),
										   dataserver=request.registry.getUtility(nti_interfaces.IDataserver) )
		if not remote_user: return

		# Walk up the parent tree of content units (not including the mythical root)
		# until we run out, or find preferences
		prefs = None
		contentUnit = context.contentUnit
		while lib_interfaces.IContentUnit.providedBy(contentUnit):
			container = remote_user.getContainer( contentUnit.ntiid )
			prefs = app_interfaces.IContentUnitPreferences( container, None )
			if prefs and prefs.sharedWith:
				break
			contentUnit = contentUnit.__parent__
			prefs = None

		if prefs and prefs.sharedWith:
			ext_obj = {}
			ext_obj['State'] = 'set' if contentUnit is context.contentUnit else 'inherited'
			ext_obj['Provenance'] = contentUnit.ntiid
			ext_obj['sharedWith'] = prefs.sharedWith
			ext_obj['Class'] = 'SharingPagePreference'
			result_map['sharingPreference'] = ext_obj


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.contentlibrary.interfaces.IContentUnit',
			  permission=nauth.ACT_READ, request_method='GET' )
def _LibraryTOCRedirectView(request, default_href=None, ntiid=None):
	"""
	Given an :class:`lib_interfaces.IContentUnit`, redirect the request to the static content.
	This allows unifying handling of NTIIDs.

	If the client uses the Accept header to ask for a Link to the content, though,
	then return that link; the client will do the redirection manually. (This is helpful
	for clients that need to know the URL of the content and which are using libraries
	that otherwise would swallow it and automatically redirect.)

	This also works when used as a view named for the ROOT ntiid; no href is possible, but the rest
	of the data can be returned.
	"""
	href = getattr(request.context, 'href', default_href )
	lastModified = 0
	# Right now, the ILibraryTOCEntries always have relative hrefs,
	# which may or may not include a leading /.
	# TODO: We're assuming these map into the URL space
	# based in their root name. Is that valid? Do we need another mapping layer?
	if not href.startswith( '/' ):
		root = traversal.find_interface( request.context, lib_interfaces.IContentPackage )
		if root: # missing in the root ntiid case
			lastModified = getattr( root, 'lastModified', 0 ) # only IFilesystemContentPackage guaranteed to have
			href = root.root + '/' + href
			href = href.replace( '//', '/' )
			if not href.startswith( '/' ):
				href = '/' + href

	# If the client asks for a specific type of data,
	# a link, then give it to them. Otherwise...
	link_mt = nti_mimetype_with_class( 'link' )
	link_mt_json = link_mt + '+json'
	json_mt = 'application/json'
	page_info_mt = nti_mimetype_with_class( 'pageinfo' )
	page_info_mt_json = page_info_mt + '+json'

	mts = ('text/html',link_mt,link_mt_json,json_mt,page_info_mt,page_info_mt_json)
	accept_type = 'text/html'
	if request.accept:
		accept_type = request.accept.best_match( mts )

	if accept_type in (link_mt, link_mt_json):
		link = links.Link( href, rel="content" )
		# We cannot render a raw link using the code in pyramid_renderers, but
		# we need to return one to get the right mime type header. So we
		# fake it by rendering here
		def _t_e_o():
			return {"Class": "Link", "MimeType": link_mt, "href": href, "rel": "content"}
		link.toExternalObject = _t_e_o
		interface.alsoProvides( link, loc_interfaces.ILocationInfo )
		link.__parent__ = request.context
		link.__name__ = href
		link.getNearestSite = lambda: request.registry.getUtility( nti_interfaces.IDataserver ).root
		return link

	if accept_type in (json_mt,page_info_mt,page_info_mt_json):
		return _create_page_info(request, href, ntiid or request.context.ntiid, last_modified=lastModified)

	# ...send a 302. Return rather than raise so that webtest works better
	return hexc.HTTPSeeOther( location=href )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  name=ntiids.ROOT,
			  permission=nauth.ACT_READ, request_method='GET' )
def _RootLibraryTOCRedirectView(request):
	return _LibraryTOCRedirectView( request, default_href='', ntiid=request.view_name)
