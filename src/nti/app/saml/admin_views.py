#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id: views.py 94273 2016-08-15 18:55:08Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.app.saml import MessageFactory as _
from nti.app.saml import PROVIDER_INFO

from nti.app.saml.views import SAMLPathAdapter

from nti.common.maps import CaseInsensitiveDict

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser

from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

from nti.dataserver.users.users import User

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

@view_config(name=PROVIDER_INFO,
			 context=SAMLPathAdapter,
			 request_method="GET",
			 route_name='objects.generic.traversal',
			 renderer='rest',
			 permission=nauth.ACT_NTI_ADMIN)
def provider_info_view(request):
		values = CaseInsensitiveDict(request.params)
		username = values.get('username') or values.get('user')
		if not username:
			raise hexc.HTTPUnprocessableEntity(_("Must specify a username."))

		entity_id = values.get('entity_id')
		if not entity_id:
			raise hexc.HTTPUnprocessableEntity(_("Must specify entity_id."))

		user = User.get_user(username)
		if user is None or not IUser.providedBy(user):
			raise hexc.HTTPUnprocessableEntity(_("User not found."))

		return ISAMLIDPUserInfoBindings(user)[entity_id]