
#!/usr/bin/env python2.7

"""
Contains renderers for the REST api.
"""

logger = __import__('logging').getLogger(__name__)

import six
import collections


import pyramid.httpexceptions
from . import traversal
from pyramid import security as psec

from zope import interface
from zope import component
from zope.location import location
from zope.location.location import LocationProxy
from zope.location import interfaces as loc_interfaces
import zope.traversing.interfaces

from paste import httpheaders
HEADER_LAST_MODIFIED = httpheaders.LAST_MODIFIED.name

from zope.mimetype.interfaces import IContentTypeAware

from nti.externalization.externalization import to_external_representation, toExternalObject, EXT_FORMAT_JSON, EXT_FORMAT_PLIST, catch_replace_action
from nti.externalization.interfaces import StandardExternalFields
from nti.dataserver.mimetype import (MIME_BASE_PLIST, MIME_BASE_JSON,
									 MIME_EXT_PLIST, MIME_EXT_JSON,
									 nti_mimetype_from_object,
									 MIME_BASE)

from nti.dataserver import links
from nti.dataserver import users
from nti.ntiids import ntiids
from nti.dataserver import authorization as nauth

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

def _is_valid_href( target ):
	# We really want to check if this is a valid href. How best to do that?
	return isinstance( target, six.string_types ) and  target.startswith( '/' )

def render_link( parent_resource, link, nearest_site=None ):

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
	# TODO TODO: The above may no longer be correct at all
	target = link.target
	rel = link.rel
	content_type = nti_mimetype_from_object( target )

	href = None
	ntiid = getattr( target, 'ntiid', None ) \
		or getattr( target, 'NTIID', None ) \
		or (isinstance(target,six.string_types) and ntiids.is_valid_ntiid_string(target) and target)
	if ntiid and not nti_interfaces.IEnclosedContent.providedBy( target ):
		# Although enclosures have an NTIID, we want to avoid using it
		# if possible because it has a much nicer pretty url.
		href = ntiid
		# We're using ntiid as a backdoor for arbitrary strings.
		# But if it really is an NTIID, then direct it specially if
		# we can.
		# FIXME: Hardcoded paths.
		if ntiids.is_valid_ntiid_string( ntiid ):
			# Place the NTIID reference under the most specific place possible: the owner,
			# if we can get one, otherwise the global Site
			root = traversal.normal_resource_path( target.creator ) if nti_interfaces.ICreated.providedBy( target ) and target.creator else traversal.normal_resource_path( nearest_site )
			if ntiids.is_ntiid_of_type( ntiid, ntiids.TYPE_OID ):
				href = root + '/Objects/' + ntiid
			else:
				href = root + '/NTIIDs/' + ntiid

	elif _is_valid_href( target ):
		href = target
	else:
		# This will raise a LocationError if something is broken
		# in the chain. That shouldn't happen and needs to be dealt with
		# at dev time.
		__traceback_info__ = rel # next fun puts target in __traceback_info__
		href = traversal.normal_resource_path( target )

	result = None
	if href: # TODO: This should be true all the time now, right?
		# Join any additional path segments that were requested
		if link.elements:
			href = href + '/' + '/'.join( link.elements )
			# TODO: quoting
		result = { StandardExternalFields.CLASS: 'Link',
				   StandardExternalFields.HREF: href,
				   'rel': rel }
		if content_type:
			result['type'] = content_type
		if ntiids.is_valid_ntiid_string( ntiid ):
			result['ntiid'] = ntiid
		if not _is_valid_href( href ) and not ntiids.is_valid_ntiid_string( href ): # pragma: no cover
			# This shouldn't be possible anymore.
			__traceback_info__ = href, link, target, parent_resource, nearest_site
			raise zope.traversing.interfaces.TraversalError(href)

	return result

def render_externalizable(data, system):
	request = system['request']
	response = request.response

	lastMod = getattr( data, 'lastModified', 0 )
	body = toExternalObject( data, name='', registry=request.registry,
							 # Catch *nested* errors during externalization. We got this far,
							 # at least send back some data for the main object. The exception will be logged.
							 # AttributeError is usually a migration problem,
							 # LookupError is usually a programming problem.
							 # AssertionError is one or both
							 catch_components=(AttributeError,LookupError,AssertionError),
							 catch_component_action=catch_replace_action)
	try:
		body.__parent__ = request.context.__parent__
		body.__name__ = request.context.__name__
	except AttributeError: pass
	try:
		body.setdefault( StandardExternalFields.LINKS, [] )
	except: pass

	# Locate the nearest site to use as our base URL for
	# relative/unbased links
	try:
		loc_info = loc_interfaces.ILocationInfo( data )
	except TypeError:
		# Not adaptable (not located). Assume the main root.
		nearest_site = request.registry.getUtility( nti_interfaces.IDataserver ).root
	else:
		# Located. Better be able to get a site, otherwise we have a
		# broken chain.
		nearest_site = loc_info.getNearestSite()

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
		has_links = False
		try:
			has_links = StandardExternalFields.LINKS in obj # Catch lists, weak refs
		except TypeError:
			has_links = False
		if has_links:
			# Add an Edit link if it's an editable object that we own
			# and that doesn't already provide one.

			if StandardExternalFields.OID in obj \
			   and writable( obj ) \
			   and True: #user_root : # TODO: This breaks for providers, need an iface
				# TODO: This is weird, assuming knowledge about the URL structure here
				# Should probably use request ILocationInfo to traverse back up to the ISite
				if not any( [l.rel == 'edit'
							 for l in obj[StandardExternalFields.LINKS]
							 if isinstance(l, links.Link) ] ):
					# Create a path through to the *direct* object URL, without
					# using resource traversal. This remains valid in the event of name changes
					obj_root = location.Location()
					# Prefer a URL relative to the creator if we can get one, otherwise
					# go for the global one beneath the site
					obj_root.__parent__ = data.creator if nti_interfaces.ICreated.providedBy( data ) and data.creator else nearest_site
					obj_root.__name__ = 'Objects'
					target = location.Location()
					target.__parent__ = obj_root
					target.__name__ = obj[StandardExternalFields.OID]
					link = links.Link( target, rel='edit' )
					obj[StandardExternalFields.LINKS].append( link )

					# For cases that we can, make edit and the toplevel href be the same.
					# this improves caching
					obj['href'] = render_link( parent, link, nearest_site )['href']

			obj[StandardExternalFields.LINKS] = [render_link(parent, link, nearest_site) if isinstance( link, links.Link ) else link
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
		try:
			if lastMod <= 0 and HEADER_LAST_MODIFIED in body:
				lastMod = body[HEADER_LAST_MODIFIED]
			if lastMod <= 0 and 'Last Modified' in body:
				lastMod = body['Last Modified']
		except TypeError:
			pass

		if lastMod > 0:
			response.last_modified = lastMod

	response.content_type = find_content_type( request, data )
	if response.content_type.startswith( MIME_BASE ):
		# Only transform this if it was one of our objects
		if response.content_type.endswith( 'json' ):
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




		return body
