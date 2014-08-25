#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rendering for a REST-based client.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

from zope import interface
from zope import component

from zope.mimetype.interfaces import IContentTypeAware

from perfmetrics import metric

from nti.dataserver.links import Link
from nti.dataserver import traversal as nti_traversal
from nti.dataserver.links_external import render_link
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.representation import to_json_representation_externalized
from nti.externalization.externalization import toExternalObject,  catch_replace_action

from nti.mimetype.mimetype import nti_mimetype_from_object
from nti.mimetype.mimetype import MIME_BASE_JSON, MIME_EXT_JSON, MIME_BASE

from .interfaces import IResponseRenderer
from .interfaces import IExternalizationCatchComponentAction

@interface.provider(IExternalizationCatchComponentAction)
def _throw_action(*args):
	raise

def find_content_type( request, data=None ):
	"""
	Inspects the request (and the resulting data object, if given) to determine the Content-Type to send back.
	The returned string will always either end in 'json'.
	"""
	best_match = None
	full_type = b''
	if data is not None:
		content_type_aware = data if IContentTypeAware.providedBy( data ) \
							 else component.queryAdapter( data, IContentTypeAware )
		if content_type_aware:
			full_type = content_type_aware.mimeType
		else:
			full_type = nti_mimetype_from_object( data, use_class=False )

		if full_type and not full_type.startswith( MIME_BASE ):
			# If it wasn't something we control, then
			# it probably goes back as-is
			# (e.g., an image)
			return full_type

	app_json = MIME_BASE_JSON
	app_c_json = str(full_type) + MIME_EXT_JSON if full_type else MIME_BASE_JSON

	if request.accept:
		# In preference order
		offers = ( app_c_json,
				   app_json,
				   b'application/json' )
		best_match = request.accept.best_match( offers )

	if best_match:
		# Give back the most specific version possible
		if best_match.endswith( b'json' ):
			best_match = app_c_json

	if not best_match:
		best_match = app_c_json

	return best_match or MIME_BASE_JSON

@metric
@interface.provider(IResponseRenderer)
def render_externalizable(data, system):
	"""
	.. note:: As an ad-hoc protocol, if the request object has an attribute
		`_v_nti_render_externalizable_name`, then that will be the name we pass
		to :func:`toExternalObject`. Otherwise, we will use the default name.
	"""
	request = system['request']
	response = request.response
	__traceback_info__ = data, request, response, system

	body = toExternalObject( data, name=getattr(request, '_v_nti_render_externalizable_name', ''),
							 # Catch *nested* errors during externalization. We got this far,
							 # at least send back some data for the main object. The exception will be logged.
							 # AttributeError is usually a migration problem,
							 # LookupError is usually a programming problem.
							 # AssertionError is one or both
							 catch_components=(AttributeError,LookupError,AssertionError),
							 catch_component_action=component.queryUtility(IExternalizationCatchComponentAction,
																		   default=catch_replace_action),
							 request=request)
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

				# NOTE: This isn't quite right: There's no guarantee
				# about what object was mutated or what's being
				# returned. So long as the actual mutation was to the
				# actual resource object that was returned this is
				# fine, otherwise it's a bit of a lie. But returning
				# nothing isn't on option we can get away with right
				# now (Mar2013) either due to existing clients that
				# also make assumptions about how and what resource
				# was manipulated, so go with the lesser of two evils
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

	return body

@interface.implementer(IResponseRenderer)
def render_externalizable_factory(d):
	return render_externalizable

@interface.implementer(IResponseRenderer)
@component.adapter(nti_interfaces.IEnclosedContent)
def render_enclosure_factory( data ):
	"""
	If the enclosure is pure binary data, not modeled content,
	we want to simply output it without trying to introspect
	or perform transformations.
	"""
	if not nti_interfaces.IContent.providedBy( data.data ):
		return render_enclosure

@interface.provider(IResponseRenderer)
def render_enclosure( data, system ):
	request = system['request']
	response = request.response

	response.content_type = find_content_type( request, data )
	response.last_modified = data.lastModified
	return data.data
