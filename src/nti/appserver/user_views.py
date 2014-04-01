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

from zope import interface
from zope import component

from pyramid.view import view_config

from nti.dataserver.users.users_external import _avatar_url
from nti.dataserver.links_external import render_link

from .httpexceptions import HTTPFound

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.dataserver.interfaces.IUser',
			  request_method='GET',
			  name='avatar')
def avatar_view(context, request):
	"""
	Redirects to the location of the actual avatar.
	"""

	# Use a 302 response to tell clients where to go,
	# and let them cache it for awhile (a 303 is completely
	# uncachable). We expect that this method will not be
	# hit by the actual user himself, only his friends, so
	# he won't notice a stale response.

	# We use a private method to do this because we rely
	# on implementation details about the user and his data.

	url_or_link = _avatar_url(context)
	if not isinstance(url_or_link, six.string_types):
		# In this case, we have a file we're hosting.
		# What happens when the user changes or removes that file?
		# we're sending direct OID links, does it still work? Or will it 404?
		url_or_link = render_link(url_or_link)

	result = HTTPFound(url_or_link)
	# Let it be cached for a bit. gravatar uses 5 minutes
	result.cache_control.max_age = 300
	result.expires = time.time() + 300
	return result

from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.interfaces import IUser
from zc.displayname.interfaces import IDisplayNameGenerator
from pyramid.interfaces import IRequest

@interface.implementer(IDisplayNameGenerator)
@component.adapter(IUser,IRequest)
class UserDisplayNameGenerator(object):

	def __init__(self, context, request):
		self.context = context

	def __call__(self, maxlength=None):
		names = IFriendlyNamed(self.context)
		return names.alias or names.realname or self.context.username
