#!/usr/bin/env python2.7

"""
Contains renderers for the REST api.
"""
import warnings
import collections

import pyramid.httpexceptions
from pyramid import traversal
from pyramid import security as psec
from pyramid import location as plocation

from zope.location import location
from zope.location.location import LocationProxy

from paste import httpheaders
HEADER_LAST_MODIFIED = httpheaders.LAST_MODIFIED.name

from zope.mimetype.interfaces import IContentTypeAware

from nti.dataserver.datastructures import (to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST,
										   toExternalObject, StandardExternalFields)
from nti.dataserver.mimetype import (MIME_BASE_PLIST, MIME_BASE_JSON,
									 MIME_EXT_PLIST, MIME_EXT_JSON,
									 nti_mimetype_from_object,
									 MIME_BASE)

from nti.dataserver import links
from nti.dataserver import users

from . import interfaces as app_interfaces

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

def render_link( parent_resource, link, user_root_resource=None ):

	# TODO: This clearly doesn't work for links that
	# are nested. What's less obvious is that
	# trying to do the replacement during the original
	# recursion of toExternalObject doesn't work either, because the
	# hrefs can be path dependent, and we may not have a valid/correct
	# __parent__ at that time. How to fix this? This needs to
	# work for byte enclosures and object enclosures, some of which
	# might be referenced in multiple places. We could do OID links for the latter...
	# Right now, we've hacked something in with traversal after the
	# fact, and some gratuitous __parent__ attributes.
	#import pdb; pdb.set_trace()
	target = link.target
	rel = link.rel
	content_type = nti_mimetype_from_object( target )

	href = None
	ntiid = getattr( target, 'ntiid', None ) or getattr( target, 'NTIID', None )
	if ntiid:
		href = ntiid
	else:
		# let the custom URL hook, if any, be used
		resource = LocationProxy( target,
								  getattr( target, '__parent__', parent_resource ),
										   #getattr( link, '__parent__', parent_resource ) ),
								  getattr( target, '__name__', getattr( target, 'name', None )) )
		# replace the actual User object with the userrootresource if we have one
		if user_root_resource and isinstance( list(plocation.lineage(resource))[-1], users.User ):
			r = resource
			while getattr( r.__parent__, '__parent__', None):
				r = r.__parent__
			r.__parent__ = user_root_resource
		href = traversal.resource_path( resource )

	result = { StandardExternalFields.CLASS: 'Link',
			   StandardExternalFields.HREF: href,
			   'rel': rel }
	if content_type: result['type'] = content_type

	return result


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

		lastMod = getattr( data, 'lastModified', 0 )
		body = toExternalObject( data )
		try:
			body.__parent__ = request.context.__parent__
			body.__name__ = request.context.__name__
		except AttributeError: pass
		try:
			body.setdefault( StandardExternalFields.LINKS, [] )
		except: pass

		user_root = None
		if hasattr( request, 'context' ):
			user_root = traversal.find_interface( request.context, app_interfaces.IUserRootResource )
		def render_links( obj, parent=None ):
			try:
				obj.setdefault( StandardExternalFields.LINKS, [] )
			except AttributeError: pass
			if StandardExternalFields.LINKS in obj: # Catch lists
				# Add an Edit link if it's an editable object that we own
				# and that doesn't already provide one.
				if StandardExternalFields.OID in obj \
				   and StandardExternalFields.CREATOR in obj \
				   and obj[StandardExternalFields.CREATOR] == psec.authenticated_userid( request ) \
				   and user_root : # TODO: This breaks for providers, need an iface
					# TODO: This is weird, assuming knowledge about the URL structure here
					if not any( [l.rel == 'edit'
								 for l in obj[StandardExternalFields.LINKS]
								 if isinstance(l, links.Link) ] ):
						obj_root = location.Location()
						obj_root.__parent__ = user_root; obj_root.__name__ = 'Objects'
						target = location.Location()
						target.__parent__ = obj_root; target.__name__ = obj[StandardExternalFields.OID]
						link = links.Link( target, rel='edit' )
						obj[StandardExternalFields.LINKS].append( link )

				obj[StandardExternalFields.LINKS] = [render_link(parent, link, user_root) if isinstance( link, links.Link ) else link
													 for link
													 in obj[StandardExternalFields.LINKS]]
				if not obj[StandardExternalFields.LINKS]:
					del obj[StandardExternalFields.LINKS]

			for v in obj.itervalues() if isinstance( obj, collections.Mapping ) else iter(obj):
				if isinstance( v, collections.MutableMapping ):
					render_links( v, obj )
				elif isinstance( v, collections.MutableSequence ):
					for vv in v:
						if isinstance( vv, collections.MutableMapping ):
							render_links( vv, obj )

		render_links( body, request.context )

		# Search for a last modified value.
		if response.last_modified is None:
			if lastMod <= 0 and HEADER_LAST_MODIFIED in body:
				lastMod = body[HEADER_LAST_MODIFIED]
			if lastMod <= 0 and 'Last Modified' in body:
				lastMod = body['Last Modified']

			if lastMod > 0:
				response.last_modified = lastMod

		# Handle Not Modified
		if response.status_int == 200 and response.last_modified is not None and request.if_modified_since:
			# Since we know a modification date, respect If-Modified-Since. The spec
			# says to only do this on a 200 response
			if response.last_modified <= request.if_modified_since:
				raise pyramid.httpexceptions.HTTPNotModified()

		response.content_type = find_content_type( request, data )
		# our responses vary based on the Accept parameter, since
		# that informs representation
		response.vary = 'Accept'
		if response.content_type.startswith( MIME_BASE ):
			# Only transform this if it was one of our objects
			if response.content_type.endswith( 'json' ):
				body = to_external_representation( body, EXT_FORMAT_JSON )
			else:
				body = to_external_representation( body, EXT_FORMAT_PLIST )
		# TODO: ETag support. We would like to have this for If-Match as well,
		# for better deletion and editing of shared resources. For that to work,
		# we need to have this be more semantically meaningful, and happen sooner.
		# It should also be representation independent (?)
		response.md5_etag( body, True )

		return body
