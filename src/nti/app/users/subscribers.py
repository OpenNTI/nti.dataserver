#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid.threadlocal import get_current_request

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users.utils import is_email_verified

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import BlacklistedUsernameError
from nti.dataserver.users.interfaces import EmailAlreadyVerifiedError
from nti.dataserver.users.interfaces import IWillCreateNewEntityEvent
from nti.dataserver.users.interfaces import ISendEmailConfirmationEvent

from .utils import safe_send_email_verification

@component.adapter( IUser, IWillCreateNewEntityEvent )
def new_user_is_not_blacklisted(user, event):
	"""
	Verify that this new user does not exist in our blacklist of former users.
	"""
	user_blacklist = component.getUtility( IUserBlacklistedStorage )
	if user_blacklist.is_user_blacklisted( user ):
		raise BlacklistedUsernameError( user.username )

@component.adapter( IUser, IWillCreateNewEntityEvent )
def new_user_with_not_email_verified(user, event):
	ext_value = getattr(event, 'ext_value', None) or {}
	meta_data = getattr(event, 'meta_data', None) or {}
	email = ext_value.get('email')
	if 	email and meta_data.get('check_verify_email', True) and \
		is_email_verified(email):
		raise EmailAlreadyVerifiedError( email )

@component.adapter(IUser, ISendEmailConfirmationEvent)
def _send_email_confirmation(record, event):
	user = event.user
	profile = IUserProfile(user, None)
	email = getattr(profile, 'email', None)
	request = event.request or get_current_request()	
	if profile is None:
		safe_send_email_verification(user, profile, email, request)
