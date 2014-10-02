#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import urllib
import zope.intid

from zope import component
from urlparse import urlparse

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver.users.users import User
from nti.dataserver import authorization as nauth

from nti.utils.maps import CaseInsensitiveDict

K20_IDENTIFIER_NAME = 'token'
K20_VIEW_NAME = 'k20_link'
K20_LINK_PARAM_NAME = 'href'

def _get_user_token( user ):
	intids = component.getUtility( zope.intid.IIntIds )
	return intids.getId( user )

@view_config(route_name='objects.generic.traversal',
			 name=K20_VIEW_NAME,
			 request_method='GET',
			 permission=nauth.ACT_READ )
class K20Link( AbstractAuthenticatedView ):

	def __call__(self):
		request = self.request
		params = CaseInsensitiveDict( request.params )
		url = params.get( K20_LINK_PARAM_NAME )

		username = self.remoteUser
		user = User.get_user( username )
		if user is None or url is None:
			return hexc.HTTPBadRequest( "User or link invalid." )

		user_token = _get_user_token( user )

		params = urllib.urlencode( { K20_IDENTIFIER_NAME : user_token })
		if urlparse( url )[4]:
			new_link = url + '&' + params
		else:
			new_link = url + '?' + params

		return hexc.HTTPFound( location=new_link )

