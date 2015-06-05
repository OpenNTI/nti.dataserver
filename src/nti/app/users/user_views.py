#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic views for any user (or sometimes, entities).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time

from zope import component

from pyramid.view import view_config
from pyramid import httpexceptions as hexc
from pyramid.response import Response as PyramidResponse

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IMemcacheClient
from nti.dataserver.interfaces import IDataserverFolder

from nti.dataserver import authorization as nauth

from nti.dataserver.users.users_external import _avatar_url
from nti.dataserver.users.users_external import _background_url
from nti.dataserver.users.avatar_urls import get_background_image
from nti.dataserver.users.avatar_urls import get_background_image_name

from nti.links.externalization import render_link

def _image_view(context, request, func):
	"""
	Redirects to the location of the actual image.
	"""
	# Use a 302 response to tell clients where to go,
	# and let them cache it for awhile (a 303 is completely
	# uncachable). We expect that this method will not be
	# hit by the actual user himself, only his friends, so
	# he won't notice a stale response.

	# We use a private method to do this because we rely
	# on implementation details about the user and his data.

	url_or_link = func(context)
	if not isinstance(url_or_link, six.string_types):
		# In this case, we have a file we're hosting.
		# What happens when the user changes or removes that file?
		# we're sending direct OID links, does it still work? Or will it 404?
		url_or_link = render_link(url_or_link)

	result = hexc.HTTPFound(url_or_link)
	# Let it be cached for a bit. gravatar uses 5 minutes
	result.cache_control.max_age = 300
	result.expires = time.time() + 300
	return result

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IUser,
			 request_method='GET',
			 name='avatar')
def avatar_view(context, request):
	result = _image_view(context, request, _avatar_url)
	return result

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 context=IUser,
			 request_method='GET',
			 name='background')
def background_view(context, request):
	result = _image_view(context, request, _background_url)
	return result

class Response(PyramidResponse):
	default_charset = None

@view_config(route_name='objects.generic.traversal',
			 name='backgrounds',
			 request_method='GET',
			 context=IDataserverFolder,
			 permission=nauth.ACT_READ)
class BackgroundsView(AbstractAuthenticatedView):
	
	def _get_background_image(self):
		result = None
		key = "/background_images/%s" % get_background_image_name(self.remoteUser)
		mc = component.queryUtility(IMemcacheClient)
		if mc is not None:
			result = mc.get(key)

		if result is None:
			result = get_background_image(self.remoteUser)
			if mc is not None:
				mc.set(key, result)
		return result

	def __call__(self):
		request = self.request
		image = request.subpath[0] if request.subpath else ''
		if not image:
			raise hexc.HTTPNotFound()
		
		image = self._get_background_image()
		response = Response()
		response.body_file = image
		response.content_type = b'image/png'
		response.content_disposition = b'attachment; filename="image.png"'
		return response
