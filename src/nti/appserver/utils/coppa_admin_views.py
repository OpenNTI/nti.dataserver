#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Coppa admin views

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson

from pyramid.view import view_config
from pyramid import httpexceptions as hexc

from zope import component
from zope import interface

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces

from nti.appserver.utils import is_true
from nti.appserver.utils import _JsonBodyView
from nti.appserver.link_providers import flag_link_provider

_view_defaults = dict(route_name='objects.generic.traversal',
					  renderer='rest',
					  permission=nauth.ACT_READ,
					  request_method='GET')
_view_admin_defaults = _view_defaults.copy()
_view_admin_defaults['permission'] = nauth.ACT_COPPA_ADMIN

_post_view_defaults = _view_defaults.copy()
_post_view_defaults['request_method'] = 'POST'

_admin_view_defaults = _post_view_defaults.copy()
_admin_view_defaults['permission'] = nauth.ACT_COPPA_ADMIN

@view_config(name="rollback_coppa_upgraded_users", **_admin_view_defaults)
class RollbackCoppaUpgradedUsers(_JsonBodyView):

	def __call__(self):
		values = self.readInput()
		usernames = values.get('usernames', '')
		all_coppa = values.get('all', 'F')
		
		if is_true(all_coppa):
			dataserver = component.getUtility( nti_interfaces.IDataserver)
			usernames = nti_interfaces.IShardLayout(dataserver).users_folder.keys()
		else:
			usernames = usernames.split(',')

		items = []
		for username in usernames:
			user = users.User.get_user(username)
			if not user or not nti_interfaces.ICoppaUserWithAgreementUpgraded.providedBy(user):
				continue

			items.append(username)
			
			# reset interfaces
			interface.noLongerProvides(user, nti_interfaces.ICoppaUserWithAgreement)
			interface.noLongerProvides(user, nti_interfaces.ICoppaUserWithAgreementUpgraded)
			interface.alsoProvides(user, nti_interfaces.ICoppaUserWithoutAgreement)
			
			# add link
			flag_link_provider.add_link(user, 'coppa.upgraded.rollbacked')
			
		response = self.request.response
		response.content_type = b'application/json; charset=UTF-8'
		response.body = simplejson.dumps({'Count':len(items), 'Items':items})
		return hexc.HTTPNoContent()

del _view_defaults
del _post_view_defaults
del _admin_view_defaults
del _view_admin_defaults
