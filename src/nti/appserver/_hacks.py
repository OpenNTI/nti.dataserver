#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from .ugd_edit_views import UGDPutView
from nti.appserver import httpexceptions as hexc

from pyramid.view import view_config


from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver import authorization as nauth


@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context=nti_interfaces.IFriendsList,
			  name='++fields++friends',
			  permission=nauth.ACT_UPDATE, request_method='PUT' )
class _FriendsListsFriendsFieldUpdateView(UGDPutView):
	"""
	This is a temporary fast hack to enable updating friends list objects
	with just friends using the new ++fields++ syntax until the unification
	is complete.

	This is done by specifically naming a view for the remainder of the path
	after a friends list.
	"""
	# TODO: Can this go away now?
	inputClass = list

	def _get_object_to_update( self ):
		return self.request.context

	def _transformInput( self, externalValue ):
		return {"friends": externalValue}

import requests
import requests.exceptions

@view_config( route_name='objects.generic.traversal',
			  context=nti_interfaces.IDataserverFolder,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='GET',
			  request_param='image_url',
			  name="echo_image_url")
def echo_image_url(request):
	"""
	Temporary hack to circumvent cross-domain problems
	for non-CORS capable browsers, relating to image-in-canvas.
	This should only be used sparingly, and only when required. It has
	performance costs as well as monetary costs.

	To help prevent us being used as a middleman in shady scenarios,
	this is limited to authenticated users and ONLY image mime types.

	Accepts one ``GET`` paramater, ``image_url``.
	"""

	# TODO: This should do some more verification on the request.
	# TODO: Detect that the image URL comes from our CDN
	# and map it back to the original S3 bucket and return the data from
	# that. That would be internal traffic whereas the CDN request is going to be
	# external traffic and we'll pay data transfer charges.

	try:
		image_response = requests.get( request.params['image_url'], prefetch=False )
		image_response.raise_for_status()
	except requests.exceptions.HTTPError as e:
		request.response.status_code = e.response.status_code
		request.response.body = e.message
		return request.response
	except requests.exceptions.RequestException as e:
		return hexc.HTTPBadRequest( e.message )

	if not image_response.headers.get('content-type', '').lower().startswith('image/'):
		return hexc.HTTPNotFound()

	for header_name_to_copy in (b'Content-Type', b'ETag', b'Last-Modified','Content-Length'):
		header_value = image_response.headers.get( header_name_to_copy )
		if header_value:
			request.response.headers[header_name_to_copy] = header_value

	request.response.app_iter = image_response.iter_content( chunk_size=256 )
	return request.response
