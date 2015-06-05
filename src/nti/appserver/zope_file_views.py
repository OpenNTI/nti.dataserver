#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views for :mod:`zope.file` objects, and likewise :class:`zope.browserresource.interfaces.IFileResource`

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope.browserresource.interfaces import IFileResource

from zope.file import download
from zope.file.interfaces import IFile

from zope.publisher.interfaces.browser import IBrowserRequest

from pyramid.view import view_config
from pyramid.security import NO_PERMISSION_REQUIRED

from ZODB.POSException import POSKeyError

try:
	from plone.namedfile import NamedImage
except ImportError:  # pypy? Doesn't make sense
	NamedImage = None

from nti.app.externalization.view_mixins import UploadRequestUtilsMixin

from nti.app.renderers.interfaces import IPreRenderResponseCacheController

from nti.common import dataurl

from nti.dataserver import authorization as nauth
from nti.dataserver.interfaces import IDataserverFolder

from . import httpexceptions as hexc

def _do_view(request, view):
	# Best we can do is try to get good cache headers. Check this before
	# opening a blob; if etags match it raises NotModified
	controller = IPreRenderResponseCacheController(request.context)
	controller(request.context, {'request': request})

	# For the typical IFile implementation backed by a ZODB blob, this
	# opens the blob in 'committed' mode and reads the data from a
	# local file. It (the app_iter) is thus transaction and site
	# independent making it safe to pass up through any tweens that do
	# transaction and site management
	view = view(request.context, IBrowserRequest(request))
	try:
		app_iter = view()
	except POSKeyError:
		# We get this from RelStorage if the blob directory is not
		# configured correctly, typically on a new machine/new deployment.
		# The wrapping IFile object exists, but the underling blob
		# does not
		logger.exception("A blob is missing. Is the blob-storage configured correctly?")
		# 507. Not exactly right, but better than a 404 as it indicates
		# a transient situation and an error on the server
		raise hexc.HTTPInsufficientStorage()

	request.response.app_iter = app_iter
	# The correct mimetype will be set because the IFile is IContentTypeAware
	# and zope.mimetype provides an adapter from that to IContentInfo, which Display
	# uses to set the mimetype

	# Our most common use-case for this currently (whiteboard images) could benefit significantly
	# from something like putting the blobs up in S3/cloudfront and serving from there,
	# or at least not serving from the dataserver directly.
	return request.response

@view_config(route_name='objects.generic.traversal',
			 context=IFile,
			 permission=nauth.ACT_READ,
			 request_method='GET',
			 name="view")
def file_view(request):
	"""
	A view that simply returns the data of the file without setting any
	``Content-Disposition`` headers to attempt to force a download (and
	typically a display inline).

	Some ACL in the parent hierarchy must make this readable.
	"""
	return _do_view(request, download.Display)

from nti.dataserver.users.interfaces import IAvatarURL
from nti.dataserver.users.interfaces import IBackgroundURL

def _image_file_view(request, image_interface, attr_name):
	"""
	Like :func:`file_view`, but does not require the
	user to be authenticated. We take care to use this only
	for the user's avatar/background URL.
	"""
	# Alternately, we could use a custom path traverser through the
	# actual user object and in that way use a new object with a custom
	# ACL that grants everyone access. This method is a bit more hacky
	# (it depends on how the file is stored) but has slightly fewer
	# moving pieces.
	the_file = request.context
	if not image_interface.providedBy(the_file.__parent__):
		raise hexc.HTTPForbidden()

	with_url = image_interface(the_file.__parent__)
	url_property = type(with_url).avatarURL
	if url_property.get_file(with_url) is not the_file:
		raise hexc.HTTPForbidden()

	result = _do_view(request, download.Display)
	return result

@view_config(route_name='objects.generic.traversal',
			 context=IFile,
			 request_method='GET',
			 name="avatar_view")
def avatar_file_view(request):
	result = _image_file_view(request, IAvatarURL, 'avatarURL')
	return result

@view_config(route_name='objects.generic.traversal',
			 context=IFile,
			 request_method='GET',
			 name="background_view")
def background_file_view(request):
	result = _image_file_view(request, IBackgroundURL, 'backgroundURL')
	return result

@view_config(route_name='objects.generic.traversal',
			 context=IFile,
			 permission=nauth.ACT_READ,
			 request_method='GET')
@view_config(route_name='objects.generic.traversal',
			 context=IFile,
			 permission=nauth.ACT_READ,
			 request_method='GET',
			 name="download")
def file_download_view(request):
	"""
	A view that returns the data of the file for download by setting a
	``Content-Disposition`` headers to attempt to force a download.
	This is the default view for a file, and also a named view.

	Some ACL in the parent hierarchy must make this readable.
	"""
	return _do_view(request, download.Download)

@view_config(route_name='objects.generic.traversal',
			 context=IFileResource,
			 permission=NO_PERMISSION_REQUIRED,
			 request_method='GET')
def file_resource_get_view(request):
	data = request.context.GET()
	request.response.body = data
	return request.response

@view_config(route_name='objects.generic.traversal',
			 context=IFileResource,
			 permission=NO_PERMISSION_REQUIRED,
			 request_method='HEAD')
def file_resource_HEAD_view(request):
	request.context.HEAD()
	return request.response

@view_config(route_name='objects.generic.traversal',
			 context=IDataserverFolder,
			 permission=nauth.ACT_READ,  # anyone logged in...
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

	upload = UploadRequestUtilsMixin()
	upload.request = request

	data = upload._get_body_content()
	filename = upload._get_body_name()

	# Now, sniff the data with the named image type. If we don't get
	# an image type back, regardless of what they uploaded, then it's not valid
	# TODO: We could insert scaling or other manipulations here
	named_image = NamedImage(data=data, filename=filename)
	if not named_image.contentType or not named_image.contentType.startswith('image'):
		raise hexc.HTTPBadRequest(_("Not an image upload"))

	data_url = dataurl.encode(data, mime_type=named_image.contentType)

	response = request.response
	mts = (b'text/plain', b'application/json')
	accept_type = b'text/plain'
	if getattr(request, 'accept', None):
		accept_type = request.accept.best_match(mts)

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

@view_config(route_name='objects.generic.traversal',
			 context=IDataserverFolder,
			 permission=nauth.ACT_READ,  # anyone logged in...
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
	rsp = image_to_dataurl(request)

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
