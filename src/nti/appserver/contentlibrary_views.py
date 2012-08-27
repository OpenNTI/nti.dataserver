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

import sys
import time
import itertools
import warnings

from zope import interface
from zope import component
from zope.location import interfaces as loc_interfaces
from zope.annotation.factory import factory as an_factory
from zope.traversing import interfaces as trv_interfaces

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import links
from nti.dataserver import containers
from nti.dataserver.mimetype import  nti_mimetype_with_class
from nti.dataserver import authorization as nauth
from nti.dataserver import authorization_acl as nacl
from nti.ntiids import ntiids

from nti.appserver import interfaces as app_interfaces

from nti.contentlibrary import interfaces as lib_interfaces

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import to_external_object

def _create_page_info(request, href, ntiid, last_modified=0, jsonp_href=None):
	"""
	:param float last_modified: If greater than 0, the best known date for the
		modification time of the contents of the `href`.
	"""
	# Traverse down to the pages collection and use it to create the info.
	# This way we get the correct link structure

	remote_user = users.User.get_user( sec.authenticated_userid( request ), dataserver=request.registry.getUtility(nti_interfaces.IDataserver) )
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
		# NOTE: The preferences decorator may change this
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
		for_key = questions.by_file.get( getattr( context.contentUnit, 'key', None ) )
		if for_key:
			### XXX FIXME: We need to be sure we don't send back the
			# solutions and explanations right now
			result_map['AssessmentItems'] = to_external_object( for_key  )

###
# We look for content container preferences. For actual containers, we
# store the prefs as an annotation on the container.
# NOTE: This requires that the user must have created at least one object
# on the page before they can store preferences.
###

@interface.implementer(app_interfaces.IContentUnitPreferences)
@component.adapter(containers.LastModifiedBTreeContainer)
class _ContentUnitPreferences(persistent.Persistent):

	__parent__ = None
	__name__ = None
	sharedWith = None

	def __init__( self, createdTime=None, lastModified=None, sharedWith=None ):
		self.createdTime = createdTime if createdTime is not None else time.time()
		self.lastModified = lastModified if lastModified is not None else self.createdTime
		if sharedWith is not None:
			self.sharedWith = sharedWith

@interface.implementer(app_interfaces.IContentUnitPreferences)
@component.adapter(containers.LastModifiedBTreeContainer)
def _ContainerContentUnitPreferencesFactory(container):
	# TODO: If we move any of this, we'll need to remember to pass in the key=
	# argument otherwise we won't have access to the data that already exists
	return an_factory(_ContentUnitPreferences)(container)

###
# We can also look for preferences on the actual content unit
# itself. We provide an adapter for IDelimitedHierarchyContentUnit, because
# we know that :mod:`nti.contentlibrary.eclipse` may set up sharedWith
# values for us.
###
@interface.implementer(app_interfaces.IContentUnitPreferences)
@component.adapter(lib_interfaces.IDelimitedHierarchyContentUnit)
def _DelimitedHierarchyContentUnitPreferencesFactory(content_unit):
	sharedWith = getattr( content_unit, 'sharedWith', None )
	if sharedWith is None:
		return None

	prefs = _ContentUnitPreferences( createdTime=time.mktime(content_unit.created.timetuple()),
									 lastModified=time.mktime(content_unit.modified.timetuple()),
									 sharedWith=content_unit.sharedWith )
	prefs.__parent__ = content_unit
	return prefs

def _prefs_present( prefs ):
	"""
	Does `prefs` represent a valid preference stored by the user?
	Note that even a blank, empty set of targets is a valid preference;
	a None value removes the preference.
	"""
	return prefs and prefs.sharedWith is not None

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
		def units( ):
			contentUnit = context.contentUnit
			while lib_interfaces.IContentUnit.providedBy( contentUnit ):
				yield contentUnit, contentUnit.ntiid, contentUnit.ntiid
				contentUnit = contentUnit.__parent__
		# Also include the root
		root = ((None, '', ntiids.ROOT),)
		# We will go at least once through this loop
		contentUnit = provenance = prefs = None
		for contentUnit, containerId, provenance in itertools.chain( units(), iter(root) ):
			container = remote_user.getContainer( containerId )
			prefs = app_interfaces.IContentUnitPreferences( container, None )
			if _prefs_present( prefs ):
				break
			prefs = None

		if not _prefs_present( prefs ):
			# OK, nothing found by querying the user. What about looking at
			# the units themselves?
			for contentUnit, containerId, provenance in units():
				prefs = app_interfaces.IContentUnitPreferences( contentUnit, None )
				if _prefs_present( prefs ):
					break
				prefs = None

		if _prefs_present( prefs ):
			ext_obj = {}
			ext_obj['State'] = 'set' if contentUnit is context.contentUnit else 'inherited'
			ext_obj['Provenance'] = provenance
			ext_obj['sharedWith'] = prefs.sharedWith
			ext_obj['Class'] = 'SharingPagePreference'

			result_map['sharingPreference'] = ext_obj

		if prefs:
			# We found one, but it specified no sharing settings.
			# we still want to copy its last modified
			if prefs.lastModified > context.lastModified:
				result_map['Last Modified'] = prefs.lastModified
				context.lastModified = prefs.lastModified


def _with_acl( prefs ):
	"""
	Proxies the preferences object to have an ACL
	that allows only its owner to make changes.
	"""
	user = traversal.find_interface( prefs, nti_interfaces.IUser )
	if user is None: # pragma: no cover
		return prefs

	return nti_interfaces.ACLLocationProxy(
					prefs,
					prefs.__parent__,
					prefs.__name__,
					nacl.acl_from_aces( nacl.ace_allowing( user.username, nti_interfaces.ALL_PERMISSIONS ) ) )


@interface.implementer(trv_interfaces.ITraversable)
@component.adapter(containers.LastModifiedBTreeContainer)
class _ContainerFieldsTraversable(object):
	"""
	An :class:`zope.traversing.interfaces.ITraversable` for the updateable fields of a container.
	Register as a namespace traverser for the ``fields`` namespace
	"""

	def __init__( self, context, request=None ):
		self.context = context

	def traverse( self, name, remaining_path ):
		if name == 'sharingPreference':
			return _with_acl( app_interfaces.IContentUnitPreferences( self.context ) )

		raise KeyError( name ) # pragma: no cover

@interface.implementer(trv_interfaces.ITraversable)
@component.adapter(lib_interfaces.IContentUnit)
class _ContentUnitFieldsTraversable(object):
	"""
	An :class:`zope.traversing.interfaces.ITraversable` for the preferences stored on a content unit.

	Register as a namespace traverser for the ``fields`` namespace
	"""

	def __init__( self, context, request=None ):
		self.context = context
		self.request = request

	def traverse( self, name, remaining_path ):
		if name == 'sharingPreference':
			request = self.request or get_current_request()
			remote_user = users.User.get_user( sec.authenticated_userid( request ),
											   dataserver=request.registry.getUtility(nti_interfaces.IDataserver) )
			# Preferences for the root are actually stored
			# on the unnamed node
			ntiid = '' if self.context.ntiid == ntiids.ROOT else self.context.ntiid
			container = remote_user.getContainer( ntiid )
			# If we are expecting to write preferences, make sure the
			# container exists, even if it hasn't been used
			if container is None and self.request and self.request.method == 'PUT':
				container = remote_user.containers.getOrCreateContainer(ntiid )
			return _with_acl( app_interfaces.IContentUnitPreferences( container ) )

		raise KeyError( name ) # pragma: no cover

from .dataserver_pyramid_views import _UGDModifyViewBase as UGDModifyViewBase
@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=app_interfaces.IContentUnitPreferences,
			  permission=nauth.ACT_UPDATE, request_method='PUT' )
class _ContentUnitPreferencesPutView(UGDModifyViewBase):

	def _transformInput( self, value ):
		return value

	def updateContentObject( self, unit_prefs, externalValue, set_id=False, notify=True ):
		# At this time, externalValue must be a dict containing the 'sharedWith' setting
		try:
			unit_prefs.sharedWith = externalValue['sharedWith']
			unit_prefs.lastModified = time.time()
			return unit_prefs
		except KeyError:
			exc_info = sys.exc_info()
			raise hexc.HTTPUnprocessableEntity, exc_info[1], exc_info[2]

	def __call__(self):
		value = self.readInput()
		self.updateContentObject( self.request.context, value )

		# Since we are used as a field updater, we want to return
		# the object whose field we updated (as is the general rule)
		# Recall that the root is special cased as ''

		ntiid = self.request.context.__parent__.__name__ or ntiids.ROOT
		if ntiid == ntiids.ROOT:
			self.request.view_name = ntiids.ROOT
			return _RootLibraryTOCRedirectView( self.request )

		content_lib = self.request.registry.getUtility( lib_interfaces.IContentPackageLibrary )

		content_units = content_lib.pathToNTIID(ntiid)
		self.request.context = content_units[-1]
		return _LibraryTOCRedirectView( self.request )

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
	jsonp_href = None
	lastModified = 0
	# Right now, the ILibraryTOCEntries always have relative hrefs,
	# which may or may not include a leading /.
	# FIXME: We're assuming these map into the URL space
	# based in their root name. Is that valid? Do we need another mapping layer?
	root_package = traversal.find_interface( request.context, lib_interfaces.IContentPackage )
	if not href.startswith( '/' ) and '://' not in href: # Is it a relative path?
		mapper = component.queryAdapter( request.context, lib_interfaces.IContentUnitHrefMapper )
		if mapper:
			href = mapper.href or href
		elif root_package: # missing in the Root ntiid case
			# TODO: JAM: I think this only arises in elderly test code now?
		 	warnings.warn( "Assuming mapping of content unit href into URL space." )
		 	__traceback_info__ = root_package, href
		 	href = root_package.root + '/' + href
		 	href = href.replace( '//', '/' )
		 	if not href.startswith( '/' ):
		 		href = '/' + href

	if getattr( request.context, 'href', None ) and hasattr( request.context, 'does_sibling_entry_exist' ):
		# TODO: This falls down on the filesystem, the keys are currently meaningless strings
		# TODO: Many tests are not providing anywhere near a valid implementation of a content unit,
		# hence the check for does_sibling_entry_exist
		mapper = None
		jsonp_key = request.context.does_sibling_entry_exist( request.context.href + '.jsonp' )

		if jsonp_key:
			mapper = component.queryAdapter( jsonp_key, lib_interfaces.IContentUnitHrefMapper )
			if not mapper:
				# For the sake of the filesystem, check for the key within the context
				mapper = component.queryMultiAdapter( (jsonp_key, request.context), lib_interfaces.IContentUnitHrefMapper )
		if mapper:
			jsonp_href = mapper.href

	if root_package: # missing in the root ntiid case
		lastModified = getattr( root_package, 'lastModified', 0 )  # only IFilesystemContentPackage guaranteed to have

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
		return _create_page_info(request, href, ntiid or request.context.ntiid, last_modified=lastModified, jsonp_href=jsonp_href)

	# ...send a 302. Return rather than raise so that webtest works better
	return hexc.HTTPSeeOther( location=href )

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  name=ntiids.ROOT,
			  permission=nauth.ACT_READ, request_method='GET' )
def _RootLibraryTOCRedirectView(request):
	return _LibraryTOCRedirectView( request, default_href='', ntiid=request.view_name)
