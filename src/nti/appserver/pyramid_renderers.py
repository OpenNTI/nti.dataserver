#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains renderers for the REST api.
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

import pyramid.httpexceptions

from zope import interface
from zope import component

from zope.mimetype.interfaces import IContentTypeAware

from nti.externalization.externalization import to_external_representation, toExternalObject,  EXT_FORMAT_PLIST, catch_replace_action
from nti.externalization.externalization import to_json_representation_externalized
from nti.externalization.oids import to_external_ntiid_oid
from nti.dataserver.mimetype import (MIME_BASE_PLIST, MIME_BASE_JSON,
									 MIME_EXT_PLIST, MIME_EXT_JSON,
									 nti_mimetype_from_object,
									 MIME_BASE)


from nti.dataserver import traversal as nti_traversal
from nti.dataserver.links import Link
from nti.dataserver.links_external import render_link

import nti.appserver.interfaces as app_interfaces
import nti.dataserver.interfaces as nti_interfaces
from nti.contentlibrary import interfaces as lib_interfaces
from nti.externalization import interfaces as ext_interfaces
from .interfaces import IPreRenderResponseCacheController, IResponseRenderer, IResponseCacheController
from zope.file import interfaces as zf_interfaces

from nti.appserver import traversal
from ._view_utils import get_remote_user
from pyramid.threadlocal import get_current_request

from perfmetrics import metric

def find_content_type( request, data=None ):
	"""
	Inspects the request to determine the Content-Type to send back.
	The returned string will always either end in 'json' or
	'plist'.
	"""
	best_match = None
	full_type = b''
	if data is not None:
		content_type_aware = data if IContentTypeAware.providedBy( data ) \
							 else component.queryAdapter( data, IContentTypeAware )
		if content_type_aware:
			full_type = content_type_aware.mimeType
		else:
			full_type = nti_mimetype_from_object( data )

		if full_type and not full_type.startswith( MIME_BASE ):
			# If it wasn't something we control, then
			# it probably goes back as-is
			# (e.g., an image)
			return full_type

	app_json = MIME_BASE_JSON
	app_plst = MIME_BASE_PLIST
	app_c_json = str(full_type) + MIME_EXT_JSON if full_type else MIME_BASE_JSON
	app_c_plst = str(full_type) + MIME_EXT_PLIST if full_type else MIME_BASE_PLIST

	if request.accept:
		# In preference order
		offers = ( app_c_json, app_c_plst,
				   app_json, app_plst,
				   b'application/json', b'application/xml' )
		best_match = request.accept.best_match( offers )

	if best_match:
		# Give back the most specific version possible
		if best_match.endswith( b'json' ):
			best_match = app_c_json
		else:
			best_match = app_c_plst

	# Legacy support: Base the return off of a query param. We
	# allow this to override the Accept: header to non-default for legacy
	# reasons (and also for command-line usage)
	if request.GET.get( b'format' ) == b'plist':
		best_match = app_c_plst
	elif not best_match:
		best_match = app_c_json

	return best_match or MIME_BASE_JSON

@metric
def render_externalizable(data, system):
	request = system['request']
	response = request.response
	__traceback_info__ = data, request, response, system

	body = toExternalObject( data, name='',
							 # Catch *nested* errors during externalization. We got this far,
							 # at least send back some data for the main object. The exception will be logged.
							 # AttributeError is usually a migration problem,
							 # LookupError is usually a programming problem.
							 # AssertionError is one or both
							 catch_components=(AttributeError,LookupError,AssertionError),
							 catch_component_action=catch_replace_action)
	# There's some possibility that externalizing an object alters its
	# modification date (usually decorators do this), so check it after externalizing
	lastMod = getattr( data, 'lastModified', 0 )
	try:
		body.__parent__ = request.context.__parent__
		body.__name__ = request.context.__name__
	except AttributeError: pass

	# Everything possible should have an href on the way out. If we have no other
	# preference, and the request did not mutate any state that could invalidate it,
	# use the URL that was requested.
	if isinstance( body, collections.MutableMapping ):
		if 'href' not in body or not nti_traversal.is_valid_resource_path( body['href'] ):
			if request.method == 'GET':
				# safe assumption, send back what we had
				body['href'] = request.path_qs
			elif data:
				# Can we find one?
				# NOTE: This isn't quite right: There's no guarantee about what object was mutated
				# or what's being returned. So long as the actual mutation was to the actual resource object
				# that was returned this is fine, otherwise it's a bit of a lie.
				# But returning nothing isn't on option we can get away with right now (Mar2013) either due to existing
				# clients that also make assumptions about how and what resource was manipulated, so go with the lesser of two evils
				# that mostly works.
				try:
					link = Link(to_external_ntiid_oid( data ) if not nti_interfaces.IShouldHaveTraversablePath.providedBy( data ) else data)
					body['href'] = render_link( link )['href']
				except (KeyError,ValueError,AssertionError):
					pass # Nope


	# Search for a last modified value.
	# We take the most recent one we can find
	if response.last_modified is None:
		try:
			lastMod = max( body['Last Modified'] or 0, lastMod ) # must not send None to max()
		except (TypeError, KeyError):
			pass

		if lastMod > 0:
			response.last_modified = lastMod
			if isinstance( body, collections.MutableMapping ):
				body['Last Modified'] = lastMod

	response.content_type = str(find_content_type( request, data )) # headers must be bytes
	if response.content_type.startswith( MIME_BASE ):
		# Only transform this if it was one of our objects
		if response.content_type.endswith( b'json' ):
			body = to_json_representation_externalized( body )
		else:
			body = to_external_representation( body, EXT_FORMAT_PLIST )

	return body

@interface.implementer(app_interfaces.IResponseRenderer)
@component.adapter(nti_interfaces.IEnclosedContent)
def render_enclosure_factory( data ):
	"""
	If the enclosure is pure binary data, not modeled content,
	we want to simply output it without trying to introspect
	or perform transformations.
	"""
	if not nti_interfaces.IContent.providedBy( data.data ):
		return render_enclosure

def render_enclosure( data, system ):
	request = system['request']
	response = request.response

	response.content_type = find_content_type( request, data )
	response.last_modified = data.lastModified
	return data.data

def _get_remote_username(request=None):
	# We use the direct access to the
	# repoze information rather than the abstractions because it's slightly faster
	if request is None:
		request = get_current_request()
	if request is None:
		return ''

	environ = request.environ
	return environ.get( 'repoze.who.identity', {} ).get( 'repoze.who.userid' )

def default_vary_on( request ):
	vary_on = []
	# It is important to be consistent with these responses;
	# they should not change if the header is absent from the request
	# since it is an implicit parameter in our decision making

	# our responses vary based on the Accept parameter, since
	# that informs representation
	vary_on.append( b'Accept' )
	vary_on.append( b'Accept-Encoding' ) # we expect to be gzipped
	vary_on.append( b'Origin' )

	#vary_on.append( b'Host' ) # Host is always included
	return vary_on

def default_cache_controller( data, system ):
	request = system['request']
	response = request.response
	vary_on = default_vary_on( request )

	def _prep_cache(rsp):
		rsp.vary = vary_on
		rsp.cache_control.must_revalidate = True
		# If we have applied an Last Modified date, but we do not give any indication of
		# freshness, then some heuristics come into play that can screw us over.
		# Such a response "allows a cache to assign its own freshness lifetime" and if something
		# is defined as fresh, 'must-revalidate' is meaningless.
		# Moreover, if no freshness is provided, then it is assumed to be fresh
		# "if the cache has seen the representation recently, and it was modified relatively long ago."
		# We set some age guideline here to avoid that trap:
		if rsp.cache_control.max_age is None:
			rsp.cache_control.max_age = 0 # You must opt-in for some non-zero lifetime
			# (Setting it to 0 is equivalent to setting no-cache)

		if _get_remote_username(request) is not None:
			rsp.cache_control.private = True

	end_to_end_reload = False # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9.4
	if request.pragma == 'no-cache' or request.cache_control.no_cache: # None if not set, '*' if set without names
		end_to_end_reload = True

	# We provide non-semantic ETag support based on the current rendering.
	# This lets us work with user-specific things like edit links and user
	# online status, but it is not the most efficient way to do things.
	# It does let is support 'If-None-Match', but it does not let us support
	# If-Match, unfortunately.

	if not response.etag:
		body = system.get('nti.rendered')
		if body is not None:
			response.md5_etag( body, set_content_md5=True )
	if response.etag and request.accept_encoding and 'gzip' in request.accept_encoding and not response.etag.endswith(b'./gz'):
		# The etag is supposed to vary between encodings
		response.etag += b'./gz'

	if not end_to_end_reload and response.status_int == 200: # We will do caching
		# If they give us both an etag and a last-modified, and the etag doesn't match,
		# we MUST NOT generate a 304. Last-Modified is considered a weak validater,
		# and we could in theory still generate a 304 if etag matched and last-mod didn't.
		# However, we're going for strong semantics.
		votes = []
		if response.etag and request.if_none_match:
			votes.append( response.etag in request.if_none_match )

		# Not Modified must also be true, if given
		if response.last_modified is not None and request.if_modified_since:
			votes.append( response.last_modified <= request.if_modified_since )
			# Since we know a modification date, respect If-Modified-Since. The spec
			# says to only do this on a 200 response
			# This is a pretty poor time to do it, after we've done all this work

		if votes and all(votes):
			not_mod = pyramid.httpexceptions.HTTPNotModified()
			not_mod.last_modified = response.last_modified
			not_mod.cache_control = response.cache_control
			_prep_cache( not_mod )
			if response.etag:
				not_mod.etag = response.etag
			raise not_mod

	response.vary = vary_on
	# We also need these to be revalidated; allow the original response
	# to override, trumped by the original request
	if end_to_end_reload:
		# No, that's not right. That gets us into an endless cycle with the client
		# and us bouncing 'no-cache' back and forth
		#response.cache_control.no_cache = True
		#response.pragma = 'no-cache'
		# so lets try something more subtle
		response.cache_control.max_age = 0
		response.cache_control.proxy_revalitade = True
		response.cache_control.must_revalitade = True
		response.expiration = 0

	elif not response.cache_control.no_cache and not response.cache_control.no_store:
		_prep_cache( response )

	return response


@interface.provider( app_interfaces.IResponseCacheController )
def uncacheable_cache_controller( data, system ):
	request = system['request']
	response = request.response

	response.cache_control.no_cache = True
	return response

@interface.implementer(app_interfaces.IResponseCacheController)
@component.adapter(app_interfaces.IUncacheableInResponse)
def uncacheable_factory( data ):
	return uncacheable_cache_controller

@interface.provider( app_interfaces.IResponseCacheController )
def unmodified_cache_controller( data, system ):
	"""
	Use this when the response shouldn't be cached based on last modified dates, and we have
	no valid Last-Modified data to provide the browser (any that
	we think we have so far is invalid for some reason and will be
	discarded).

	This still allows for etag based caching.
	"""
	request = system['request']
	response = request.response
	response.last_modified = None #
	request.if_modified_since = None
	response = default_cache_controller( data, system )
	response.last_modified = None # in case it changed

@interface.implementer(app_interfaces.IResponseCacheController)
@component.adapter(app_interfaces.IUnModifiedInResponse)
def unmodified_factory( data ):
	return unmodified_cache_controller

from hashlib import md5

def md5_etag( *args ):
	digest = md5()
	for arg in args:
		if arg:
			digest.update( arg.encode('utf-8') if isinstance(arg,unicode) else str(arg) )
	return digest.digest().encode( 'base64' ).replace( '\n', '' ).strip( '=' )
_md5_etag = md5_etag

@interface.implementer(app_interfaces.IPreRenderResponseCacheController)
def UseTheRequestContextCacheController(context):
	"""
	Instead of using the return value from the view, use the context of the request.
	This is useful when the view results are directly derived from the context,
	and the context has more useful information than the result does. It allows
	you to register an adapter for the context, and use that *before* calculating the
	view. If you do have to calculate the view, you are assured that the ETag values
	that the view results create are the same as the ones you checked against.
	"""
	# TODO: We could probably detect that response.etag has been set, and
	# not do this again. The common case is that the object we are going to return
	# here would already have been called on the context before the view executed;
	# we are called after the view. Nothing should have changed on the context object in the
	# meantime.
	return app_interfaces.IPreRenderResponseCacheController( get_current_request().context )

@interface.implementer(app_interfaces.IPreRenderResponseCacheController)
class _AbstractReliableLastModifiedCacheController(object):
	"""
	Things that have reliable last modified dates go here
	for pre-rendering etag support.
	"""

	def __init__( self, context, request=None ):
		self.context = context
		self.request = request

	max_age = 300

	@property
	def _context_specific(self):
		return ()

	@property
	def _context_lastModified(self):
		return self.context.lastModified

	def __call__( self, context, system ):
		request = system['request']
		self.request = request
		response = request.response
		last_modified = self._context_lastModified
		response.last_modified = last_modified
		response.etag = _md5_etag( bytes(last_modified), _get_remote_username( request ), *self._context_specific )
		response.cache_control.max_age = self.max_age # arbitrary
		# Let this raise the not-modified if it will
		return default_cache_controller( context, system )

@component.adapter(zf_interfaces.IFile)
class _ZopeFileCacheController(_AbstractReliableLastModifiedCacheController):
	# All of our current uses of zope file objects replace them with
	# new objects, they don't overwrite. so we can use the _p_oid and _p_serial

	max_age = 3600 # an hour

	@property
	def _context_lastModified(self):
		try:
			return self.context.lastModified
		except AttributeError:
			last_mod_parent = traversal.find_interface( self.request.context, nti_interfaces.ILastModified )
			if last_mod_parent is not None:
				return last_mod_parent.lastModified

	@property
	def _context_specific(self):
		return self.context._p_oid, self.context._p_serial


@interface.implementer(app_interfaces.IPreRenderResponseCacheController)
@component.adapter(nti_interfaces.IEntity)
class _EntityCacheController(_AbstractReliableLastModifiedCacheController):
	"""
	Entities have reliable last modified dates. We use this to
	produce an ETag without rendering. We also adjust the cache
	expiration.
	"""

	@property
	def _context_specific(self):
		return (self.context.username,)

@interface.implementer(app_interfaces.IPreRenderResponseCacheController)
@component.adapter(nti_interfaces.IUser)
class _UserCacheController(_EntityCacheController):
	"""
	Adds the presence info to etag calculation.
	"""

	@property
	def _context_specific(self):
		result = _EntityCacheController._context_specific.fget(self)
		ext = {}
		dec = component.getAdapter(self.context,
								   ext_interfaces.IExternalObjectDecorator,
								   name='presence' )
		dec.decorateExternalObject(self.context, ext )
		result += (ext.get('Presence', 'Offline'),)
		return result

@interface.implementer(app_interfaces.IPreRenderResponseCacheController)
@component.adapter(nti_interfaces.IModeledContent)
class _ModeledContentCacheController(_AbstractReliableLastModifiedCacheController):
	"""
	Individual bits of modeled content have reliable last modified dates
	"""

	max_age = 0 # XXX arbitrary

	@property
	def _context_specific(self):
		try:
			return self.context.creator.username, self.context.__name__
		except AttributeError:
			return self.context.__name__,

@interface.implementer(app_interfaces.IPreRenderResponseCacheController)
@component.adapter(app_interfaces.IUGDExternalCollection)
class _UGDExternalCollectionCacheController(_AbstractReliableLastModifiedCacheController):
	"""
	UGD collections coming from this specific place have reliable last-modified dates.
	"""

	max_age = 0 # XXX arbitrary

	@property
	def _context_specific(self):
		return self.context.__name__, len(self.context)

@component.adapter(app_interfaces.ILongerCachedUGDExternalCollection)
class _LongerCachedUGDExternalCollectionCacheController(_UGDExternalCollectionCacheController):

	max_age = 120 # XXX arbitrary

@component.adapter(app_interfaces.IETagCachedUGDExternalCollection)
class _ETagCachedUGDExternalCollectionCacheController(_UGDExternalCollectionCacheController):
	# We are guaranteed to get great caching because every time the data changes
	# we change the link we generate. We don't need to take our own
	# modification date into account.

	max_age = 3600

	@property
	def _context_lastModified(self):
		return 0

@component.adapter(app_interfaces.IUserActivityExternalCollection)
class _UserActivityViewCacheController(_UGDExternalCollectionCacheController):
	"""
	If the owner asks for his own activity, we allow for less caching.
	If you ask for somebody elses, it may be slightly more stale.
	"""

	max_age = 0

	def __call__( self, context, system ):
		request = system['request']
		remote_user = get_remote_user( request )
		if remote_user and remote_user != context.__data_owner__:
			self.max_age = _LongerCachedUGDExternalCollectionCacheController.max_age
		return _UGDExternalCollectionCacheController.__call__( self, context, system )

@component.adapter(lib_interfaces.IContentPackageLibrary)
class _ContentPackageLibraryCacheController(_AbstractReliableLastModifiedCacheController):

	max_age = 120

	@property
	def _context_specific(self):
		return sorted( [x.ntiid for x in self.context.contentPackages] )

@interface.implementer(app_interfaces.IPreRenderResponseCacheController)
@component.adapter(app_interfaces.IContentUnitInfo)
class _ContentUnitInfoCacheController(object):
	# rendering this doesn't take long, and we need the rendering
	# process to decorate us with any sharing preferences that may change
	# and update our modification stamp.
	# We exist solely to change the cache age, which speeds up navigation in the app

	max_age = 300 # XXX arbitrary; we can probably go even longer?

	def __init__( self, context ):
		pass

	def __call__( self, context, system ):
		request = system['request']
		response = request.response
		if not response.cache_control.max_age:
			response.cache_control.max_age = self.max_age
		return request.response

class REST(object):

	def __init__( self, info ):
		pass

	def __call__( self, data, system ):
		request = system['request']
		response = request.response

		if response.status_int == 204:
			# No Content response is like 304 and has no body. We still
			# respect outgoing headers, though
			raise Exception( "You should return an HTTPNoContent response" )

		if data is None:
			# This cannot happen
			raise Exception( "Can only get here with a body" )

		try:
			IPreRenderResponseCacheController(data)( data, system ) # optional
		except TypeError:
			pass

		renderer = IResponseRenderer( data, render_externalizable )
		body = renderer( data, system )
		system['nti.rendered'] = body

		IResponseCacheController( data, default_cache_controller )( data, system )


		return body
