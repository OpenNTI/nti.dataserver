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

from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.appserver import traversal
from nti.appserver.z3c_zpt import PyramidZopeRequestProxy

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

	result = download.Display( request.context, PyramidZopeRequestProxy(request) )()
	request.response.app_iter = result
	# The correct mimetype will be set because the IFile is IContentTypeAware
	# and zope.mimetype provides an adapter from that to IContentInfo, which Display
	# uses to set the mimetype
	# But there is probably not a last_modified value. See if we can find one
	# in the containment (in the case of an image in a whiteboard, currently the only case,
	# this will be the Canvas object, which is perfect)
	if not request.response.last_modified:
		last_mod_parent = traversal.find_interface( request.context, nti_interfaces.ILastModified )
		if last_mod_parent:
			request.response.last_modified = last_mod_parent.lastModified
	# Our one use-case for this currently (whiteboard images) could benefit significantly
	# from something like putting the blobs up in S3/cloudfront and serving from there,
	# or at least not serving from the dataserver directly.
	return request.response
