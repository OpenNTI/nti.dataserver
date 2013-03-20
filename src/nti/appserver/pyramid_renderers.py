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
							 else request.registry.queryAdapter( data, IContentTypeAware )
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

	body = toExternalObject( data, name='', registry=request.registry,
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
			if 'Last Modified' in body:
				lastMod = max( body['Last Modified'], lastMod )
		except TypeError:
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

def default_cache_controller( data, system ):
	request = system['request']
	response = request.response
	vary_on = []
	# our responses vary based on the Accept parameter, since
	# that informs representation
	if request.accept:
		vary_on.append( b'Accept' )
	# Depending on site policies, they may also vary based on the origin
	if b'origin' in request.headers:
		vary_on.append( b'Origin' )
	if request.host:
		vary_on.append( b'Host' )

	end_to_end_reload = False # http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9.4
	if request.pragma == 'no-cache' or request.cache_control.no_cache: # None if not set, '*' if set without names
		end_to_end_reload = True
	# Handle Not Modified
	if not end_to_end_reload and response.status_int == 200 and response.last_modified is not None and request.if_modified_since:
		# Since we know a modification date, respect If-Modified-Since. The spec
		# says to only do this on a 200 response
		# This is a pretty poor time to do it, after we've done all this work
		if response.last_modified <= request.if_modified_since:
			not_mod = pyramid.httpexceptions.HTTPNotModified()
			not_mod.last_modified = response.last_modified
			not_mod.cache_control.must_revalidate = True
			not_mod.vary = vary_on
			raise not_mod

	response.vary = vary_on
	# We also need these to be revalidated; allow the original response
	# to override, trumped by the original request
	if end_to_end_reload:
		response.cache_control.no_cache = True
		response.pragma = 'no-cache'
	elif not response.cache_control.no_cache and not response.cache_control.no_store:
		response.cache_control.must_revalidate = True

	# TODO: ETag support. We would like to have this for If-Match as well,
	# for better deletion and editing of shared resources. For that to work,
	# we need to have this be more semantically meaningful, and happen sooner.
	# It should also be representation independent (?)
	# Until we have something here, don't bother computing and sending, it implies
	# false promises
	# response.md5_etag( body, True )


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
def uncacheable_no_LastModified_cache_controller( data, system ):
	"""
	Use this when the response shouldn't be cached, and we have
	no valid Last-Modified data to provide the browser (any that
	we think we have so far is invalid for some reason and will be
	discarded).
	"""

	response = uncacheable_cache_controller( data, system )
	response.last_modified = None # Why would we do this?

@interface.implementer(app_interfaces.IResponseCacheController)
@component.adapter(app_interfaces.IUncacheableUnModifiedInResponse)
def uncacheable_unmodified_factory( data ):
	return uncacheable_no_LastModified_cache_controller

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

		renderer = request.registry.queryAdapter( data,
												  app_interfaces.IResponseRenderer,
												  default=render_externalizable )
		body = renderer( data, system )
		cacher = request.registry.queryAdapter( data,
												app_interfaces.IResponseCacheController,
												default=default_cache_controller )
		cacher(data, system)

		return body
