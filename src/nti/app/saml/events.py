#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.app.saml.interfaces import ISAMLUserCreatedEvent

from nti.dataserver.interfaces import UserEvent

from nti.dataserver.saml.interfaces import ISAMLProviderUserInfo
from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

@interface.implementer(ISAMLUserCreatedEvent)
class SAMLUserCreatedEvent(UserEvent):

	def __init__(self, idp_id, user, user_info, request):
		super(SAMLUserCreatedEvent, self).__init__(user)
		self.idp_id = idp_id
		self.user_info = user_info
		self.request = request

@component.adapter(ISAMLUserCreatedEvent)
def _user_created(event):
	attach_idp_user_info(event)

def attach_idp_user_info(event):
	idp_user_info_container = ISAMLIDPUserInfoBindings(event.user)
	if event.idp_id not in idp_user_info_container:
		# TODO: to DEBUG
		logger.info('Attaching user\'s IdP info: %s', str(event.user_info))
		idp_user_info = component.queryAdapter(event.user_info,
											   ISAMLProviderUserInfo,
											   event.idp_id)
		if idp_user_info is not None:
			idp_user_info_container[event.idp_id] = idp_user_info
		else:
			logger.warn('Failed to adapt "%s" to ISAMLProviderUserInfo for user "%s", event "%s"',
						event.user_info,
						event.user.username,
						event)
	else:
		logger.info('Skipping attachment of user''s IdP info: %s', str(event.user_info))
