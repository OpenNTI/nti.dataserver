#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for :mod:`zope.file` objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config

from zope.file import download
import zope.file.interfaces

try:
	from plone.namedfile import NamedImage
except ImportError: # pypy? Doesn't make sense
	NamedImage = None

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.utils import dataurl

from . import interfaces as app_interfaces
from nti.appserver import httpexceptions as hexc
from ._pyramid_zope_integrations import PyramidZopeRequestProxy
from nti.appserver._view_utils import UploadRequestUtilsMixin


@view_config( route_name='objects.generic.traversal',
			  context=zope.file.interfaces.IFile,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='GET',
			  name="view")
def file_view(request):
	"""
	A view that simply returns the data of the file without setting any
	``Content-Disposition`` headers to attempt to force a download.
	Some ACL in the parent hierarchy must make this readable.
	"""

	# For the typical IFile implementation backed by a ZODB blob,
	# this opens the blob in 'committed' mode and reads the data from a local file.
	# It is thus transaction and site independent making it safe to pass up through
	# any tweens that do transaction and site management
	view = download.Display( request.context, PyramidZopeRequestProxy(request) )
	app_iter = view()
	request.response.app_iter = app_iter
	# The correct mimetype will be set because the IFile is IContentTypeAware
	# and zope.mimetype provides an adapter from that to IContentInfo, which Display
	# uses to set the mimetype

	# Our one use-case for this currently (whiteboard images) could benefit significantly
	# from something like putting the blobs up in S3/cloudfront and serving from there,
	# or at least not serving from the dataserver directly.

	# Best we can do is try to get good cache headers
	app_interfaces.IPreRenderResponseCacheController(request.context)(request.context, {'request': request} )

	return request.response

@view_config( route_name='objects.generic.traversal',
			  context=nti_interfaces.IDataserverFolder,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='POST',
			  name="image_to_dataurl")
def image_to_dataurl(request):
	"""
	A view intended as a helper for legacy browsers. When a form
	containing a single file naming an image is POST'd,
	echos it back as a ``data`` URL, as described in :mod:`~nti.utils.dataurl`.

	If the ``Accept`` header specifies JSON, then the value will be returned in a
	JSON dictionary, having keys ``dataurl``, ``width_px``, ``height_px`` and
	``file_size``.
	"""

	upload = UploadRequestUtilsMixin( )
	upload.request = request

	data = upload._get_body_content()
	filename = upload._get_body_name()

	# Now, sniff the data with the named image type. If we don't get
	# an image type back, regardless of what they uploaded, then it's not
	# valid
	# TODO: We could insert scaling or other manipulations here
	named_image = NamedImage( data=data, filename=filename )
	if not named_image.contentType or not named_image.contentType.startswith( 'image' ):
		raise hexc.HTTPBadRequest("Not an image upload")

	data_url = dataurl.encode( data, mime_type=named_image.contentType )

	response = request.response
	mts = (b'text/plain',b'application/json')
	accept_type = b'text/plain'
	if getattr(request, 'accept', None):
		accept_type = request.accept.best_match( mts )

	if not accept_type or accept_type == b'text/plain':
		response.content_type = b'text/plain'
		response.body = data_url
	else:
		response.content_type = accept_type
		width, height = named_image.getImageSize()
		file_size = named_image.getSize()
		response.json_body = { 'dataurl': data_url,
							   'width_px': width,
							   'height_px': height,
							   'file_size': file_size }
	return response

@view_config( route_name='objects.generic.traversal',
			  context=nti_interfaces.IDataserverFolder,
			  permission=nauth.ACT_READ, # anyone logged in...
			  request_method='POST',
			  name="image_to_dataurl_extjs")
def image_to_dataurl_extjs(request):
	"""
	Demonstrating once again the frailties of massive monolithic frameworks, ExtJS <= 4.1
	has hardcoded, REST-violating, badly broken assumptions encoded into its
	form submission logic. This method exists only for use by broken ExtJS versions
	and does undocumented, black magic-y things to try to make the behemoth happy.
	"""

	# To start with, it just /assumes/ that it's going to get json data back. Apparently
	# headers haven't been invented
	request.accept = b'application/json'
	rsp = image_to_dataurl( request )

	# Then, it further assumes that there is a redundant 'success' value
	# in the json body. Status codes also don't exist, and layer boundaries are meaningless
	body = dict(rsp.json_body)
	body['success'] = True
	# IE9 will prompt the user to save the response for application/*
	# content-types when not loading through a XHR, so we have to lie about
	# the response type, which confuses many tools but makes IE happy
	rsp.content_type = b'text/plain'
	rsp.json_body = body
	return rsp
