
#!/usr/bin/env python

"""
Contains renderers for the REST api.
"""

logger = __import__('logging').getLogger(__name__)

import collections

import pyramid.httpexceptions
import pyramid.traversal

from zope import interface
from zope import component


from paste import httpheaders
HEADER_LAST_MODIFIED = httpheaders.LAST_MODIFIED.name

from zope.mimetype.interfaces import IContentTypeAware

from nti.externalization.externalization import to_external_representation, toExternalObject,  EXT_FORMAT_PLIST, catch_replace_action
from nti.externalization.externalization import EXT_FORMAT_JSON

from nti.dataserver.mimetype import (MIME_BASE_PLIST, MIME_BASE_JSON,
									 MIME_EXT_PLIST, MIME_EXT_JSON,
									 nti_mimetype_from_object,
									 MIME_BASE)


from nti.dataserver import traversal as nti_traversal



import nti.appserver.interfaces as app_interfaces

import nti.dataserver.interfaces as nti_interfaces

def find_content_type( request, data=None ):
	"""
	Inspects the request to determine the Content-Type to send back.
	The returned string will always either end in 'json' or
	'plist'.
	"""
	best_match = None
	full_type = ''
	if data is not None:
		content_type_aware = data if IContentTypeAware.providedBy( data ) \
							 else request.registry.queryAdapter( data, IContentTypeAware )
		if content_type_aware:
			full_type = content_type_aware.mime_type
		else:
			full_type = nti_mimetype_from_object( data )

		if full_type and not full_type.startswith( MIME_BASE ):
			# If it wasn't something we control, then
			# it probably goes back as-is
			# (e.g., an image)
			return full_type

	app_json = MIME_BASE_JSON
	app_plst = MIME_BASE_PLIST
	app_c_json = full_type + MIME_EXT_JSON if full_type else MIME_BASE_JSON
	app_c_plst = full_type + MIME_EXT_PLIST if full_type else MIME_BASE_PLIST

	if request.accept:
		# In preference order
		offers = ( app_c_json, app_c_plst,
				   app_json, app_plst,
				   'application/json', 'application/xml' )
		best_match = request.accept.best_match( offers )

	if best_match:
		# Give back the most specific version possible
		if best_match.endswith( 'json' ):
			best_match = app_c_json
		else:
			best_match = app_c_plst

	# Legacy support: Base the return off of a query param. We
	# allow this to override the Accept: header to non-default for legacy
	# reasons (and also for command-line usage)
	if request.GET.get( 'format' ) == 'plist':
		best_match = app_c_plst
	elif not best_match:
		best_match = app_c_json

	return best_match or MIME_BASE_JSON

from nti.dataserver.links_external import render_link

def render_externalizable(data, system):
	request = system['request']
	response = request.response

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
	# preference, use the URL that was requested.
	if isinstance( body, collections.MutableMapping ):
		if 'href' not in body or not nti_traversal.is_valid_resource_path( body['href'] ):
			body['href'] = request.path

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

	response.content_type = str(find_content_type( request, data ))
	if response.content_type.startswith( MIME_BASE ):
		# Only transform this if it was one of our objects
		if response.content_type.endswith( 'json' ):
			# Notice that we're not doing this:
			#body = json.dumps( body )
			# Although it would be nice to avoid the second iteration that happens
			# with to_external_representation (for a 10% perf improvement), we have at
			# least one test that fails if we do that because a Link object added during
			# decoration doesn't get rendered. TODO: We could probably use simplejson's
			# object writing hook to catch that on the way out?
			body = to_external_representation( body, EXT_FORMAT_JSON )
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

	# Handle Not Modified
	if response.status_int == 200 and response.last_modified is not None and request.if_modified_since:
		# Since we know a modification date, respect If-Modified-Since. The spec
		# says to only do this on a 200 response
		# This is a pretty poor time to do it, after we've done all this work
		if response.last_modified <= request.if_modified_since:
			not_mod = pyramid.httpexceptions.HTTPNotModified()
			not_mod.last_modified = response.last_modified
			not_mod.cache_control = 'must-revalidate'
			not_mod.vary = 'Accept'
			raise not_mod

	# our responses vary based on the Accept parameter, since
	# that informs representation
	response.vary = 'Accept'
	# We also need these to be revalidated
	response.cache_control = 'must-revalidate'

	# TODO: ETag support. We would like to have this for If-Match as well,
	# for better deletion and editing of shared resources. For that to work,
	# we need to have this be more semantically meaningful, and happen sooner.
	# It should also be representation independent (?)
	# Until we have something here, don't bother computing and sending, it implies
	# false promises
	# response.md5_etag( body, True )

@interface.implementer(app_interfaces.IResponseCacheController)
@component.adapter(app_interfaces.IUncacheableInResponse)
def uncacheable_factory( data ):
	return uncacheable_cache_controller

def uncacheable_cache_controller( data, system ):
	request = system['request']
	response = request.response

	response.cache_control = 'no-store'
	response.last_modified = None

from cStringIO import StringIO
import gzip


class REST(object):

	def __init__( self, info ):
		self.dataserver = None

	def __call__( self, data, system ):
		request = system['request']
		response = request.response

		if self.dataserver and (response.status_int >= 200 and response.status_int <= 399):
			# TODO: Under what circumstances should we autocommit like this?
			# IN this fashion we are almost always committing, except on error.
			# We do this because we need to ensure that the OID is set on outgoing
			# objects.
			self.dataserver.commit()

		if response.status_int == 204:
			# No Content response is like 304 and has no body. We still
			# respect outgoing headers, though
			raise Exception( "You should return an HTTPNoContent response" )


		if data is None:
			# This cannot happen
			raise Exception( "Can only get here with a body" )

		renderer = request.registry.queryAdapter( data, app_interfaces.IResponseRenderer,
												 default=render_externalizable )
		body = renderer( data, system )
		cacher = request.registry.queryAdapter( data, app_interfaces.IResponseCacheController,
												default=default_cache_controller )
		cacher(data, system)

		# We are applying caching here. We probably don't have a proxy in front of us
		# that can filter that (sadly). The Paste gzip middleware seems to have a problem
		# in our setup...which is actually our fault. If we get any Unicode values
		# in the headers, gunicorn throws a UnicodeDecodeError. We have to be very careful
		# about that
		# TODO: Streaming
		if response.content_type.endswith( 'json' ) and 'gzip' in request.accept_encoding:
			response.content_encoding = b'gzip'
			strio = StringIO()
			gzipped = gzip.GzipFile( fileobj=strio, mode='wb' )
			gzipped.write( body )
			gzipped.close()
			body = strio.getvalue()

		return body
