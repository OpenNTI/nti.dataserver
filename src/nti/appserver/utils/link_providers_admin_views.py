#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Store admin views

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from zope.annotation import IAnnotations

from pyramid.security import authenticated_userid

from nti.appserver import logon
from nti.appserver.link_providers import link_provider

from nti.dataserver import users
from nti.dataserver import authorization as nauth

_view_defaults = dict(route_name='objects.generic.traversal',
					  renderer='rest',
					  permission=nauth.ACT_READ,
					  request_method='GET')
_view_admin_defaults = _view_defaults.copy()
_view_admin_defaults['permission'] = nauth.ACT_MODERATE

_post_view_defaults = _view_defaults.copy()
_post_view_defaults['request_method'] = 'POST'

_admin_view_defaults = _post_view_defaults.copy()
_admin_view_defaults['permission'] = nauth.ACT_MODERATE

class _PostView(object):

	def __init__(self, request):
		self.request = request

	def readInput(self):
		request = self.request
		values = simplejson.loads(unicode(request.body, request.charset))
		return values

@view_config(name="reset_initial_tos_page", **_admin_view_defaults)
class ResetInitialTOSPage(_PostView):

	def __call__(self):
		values = self.readInput()
		username = values.get('username', authenticated_userid(self.request))
		user = users.User.get_user(username)
		if not user:
			raise hexc.HTTPNotFound(detail='User not found')

		link_dict = IAnnotations(user).get(link_provider._GENERATION_LINK_KEY, None)
		if link_dict is not None:
			link_dict[logon.REL_INITIAL_TOS_PAGE] = ''
			logger.info("Resetting initial TOS page for user %s" % user)

		return hexc.HTTPNoContent()

del _view_defaults
del _post_view_defaults
del _admin_view_defaults
del _view_admin_defaults
