#!/usr/bin/env python2.7

"""
Contains renderers for the REST api.
"""
import logging
logger = logging.getLogger(__name__)

import six
import collections

import pyramid.httpexceptions
from . import traversal
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
from nti.dataserver import ntiids
from nti.dataserver import authorization as nauth

import nti.appserver.interfaces as app_interfaces

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

def _is_valid_href( target ):
	# We really want to check if this is a valid href. How best to do that?
	return isinstance( target, six.string_types ) and  target.startswith( '/' )

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
	target = link.target
	rel = link.rel
	content_type = nti_mimetype_from_object( target )

	href = None
	ntiid = getattr( target, 'ntiid', None ) \
		or getattr( target, 'NTIID', None ) \
		or (isinstance(target,six.string_types) and ntiids.is_valid_ntiid_string(target) and target)
	if ntiid:
		href = ntiid
		# We're using ntiid as a backdoor for arbitrary strings.
		# But if it really is an NTIID, then direct it specially if
		# we can.
		# FIXME: Hardcoded paths.
		if ntiids.is_valid_ntiid_string( ntiid ):
			#from IPython.core.debugger import Tracer; debug_here = Tracer()()
			root = traversal.normal_resource_path( user_root_resource ) if user_root_resource else '/dataserver2'
			if ntiids.is_ntiid_of_type( ntiid, ntiids.TYPE_OID ):
				href = root + '/Objects/' + ntiid
			else:
				href = root + '/NTIIDs/' + ntiid

	elif _is_valid_href( target ):
		href = target
	else:
		# let the custom URL hook, if any, be used
		resource = LocationProxy( target,
								  getattr( target, '__parent__', parent_resource ),
										   #getattr( link, '__parent__', parent_resource ) ),
								  getattr( target, '__name__',
										   getattr( target, 'name', (target if isinstance(target,six.string_types) else None) )) )
		# replace the actual User object with the userrootresource if we have one,
		# by injecting it into the lineage. Note that we do this with proxies
		# to avoid changing the persistent objects.
		if user_root_resource and traversal.find_interface( resource, users.User ):
			lineage = [user_root_resource if isinstance(x,users.User) else x
					   for x in traversal.lineage(resource)]
			lineage.reverse()

			parent = None
			for y in lineage:
				if y == user_root_resource:
					parent = user_root_resource.__parent__
				y = LocationProxy( y, parent, y.__name__ )
				parent = y
			resource = parent

		try:
			href = traversal.normal_resource_path( resource )
		except AttributeError:
			logger.exception( "Failed to traverse path to %s", resource )

	result = None
	if href:
		result = { StandardExternalFields.CLASS: 'Link',
				   StandardExternalFields.HREF: href,
				   'rel': rel }
		if content_type: result['type'] = content_type
		if not _is_valid_href( href ) and not ntiids.is_valid_ntiid_string( href ):
			logger.warn( "Generating invalid href %s for link %s parent %s root %s",
						 href, link, parent_resource, user_root_resource )
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
		#from IPython.core.debugger import Tracer; debug_here = Tracer()()
		body = toExternalObject( data, name='', registry=request.registry )
		try:
			body.__parent__ = request.context.__parent__
			body.__name__ = request.context.__name__
		except AttributeError: pass
		try:
			body.setdefault( StandardExternalFields.LINKS, [] )
		except: pass

		user_root = None
		if hasattr( request, 'context' ):
			# TODO: Remove all this reliance on the IUserRootResource
			# it breaks in several cases that we're hacking around.
			# In particular, it breaks when the entry point is UserSearch
			user_root = traversal.find_interface( request.context, app_interfaces.IUserRootResource )

		def writable(obj):
			"""
			Is the given object writable by the current user? Yes if the creator matches,
			or Yes if it is the returned object and we have permission.
			"""
			# TODO: This determination probably needs to happen as we walk down to externalize,
			# when we have the actual objects and potentially their actual ACLs
			# NOTE: We are mostly doing that now.
			if hasattr( obj, '__acl__' ):
				return psec.has_permission( nauth.ACT_UPDATE, obj, request )

			if obj is body:
				return psec.has_permission( nauth.ACT_UPDATE, data, request )

			return StandardExternalFields.CREATOR in obj \
				and obj[StandardExternalFields.CREATOR] == psec.authenticated_userid( request )

		def render_links( obj, parent=None ):
			if obj is None or not obj:
				# We might get some proxies that are not 'is None'?
				return
			try:
				obj.setdefault( StandardExternalFields.LINKS, [] )
			except AttributeError: pass

			# If we cannot iterate it, then we don't want to deal with it
			try:
				iter(obj)
			except TypeError:
				return

			if StandardExternalFields.LINKS in obj: # Catch lists
				# Add an Edit link if it's an editable object that we own
				# and that doesn't already provide one.

				if StandardExternalFields.OID in obj \
				   and writable( obj ) \
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

						# For cases that we can, make edit and the toplevel href be the same.
						# this improves caching
						obj['href'] = render_link( parent, link, user_root )['href']

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
		# Everything possible should have an href on the way out. If we have no other
		# preference, use the URL that was requested.
		if isinstance( body, collections.MutableMapping ):
			if 'href' not in body or not _is_valid_href( body['href'] ):
				body['href'] = request.path

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
