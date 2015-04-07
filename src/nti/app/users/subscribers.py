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

from nti.dataserver.users.utils import reindex_email_verification

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import BlacklistedUsernameError
from nti.dataserver.users.interfaces import IWillCreateNewEntityEvent
from nti.dataserver.users.interfaces import ISendEmailConfirmationEvent

from nti.externalization.interfaces import IObjectModifiedFromExternalEvent

from .utils import set_email_verification_time
from .utils import safe_send_email_verification

@component.adapter( IUser, IWillCreateNewEntityEvent )
def _new_user_is_not_blacklisted(user, event):
	"""
	Verify that this new user does not exist in our blacklist of former users.
	"""
	user_blacklist = component.getUtility( IUserBlacklistedStorage )
	if user_blacklist.is_user_blacklisted( user ):
		raise BlacklistedUsernameError( user.username )

@component.adapter(IUser, ISendEmailConfirmationEvent)
def _send_email_confirmation(user, event):
	profile = IUserProfile(user, None)
	email = getattr(profile, 'email', None)
	request = event.request or get_current_request()	
	if profile is not None and email:
		safe_send_email_verification(user, profile, email, request)

@component.adapter(IUser, IObjectModifiedFromExternalEvent)
def _user_modified_from_external_event(user, event):
	profile = IUserProfile(user, None)
	ext = event.external_value or {}
	if profile and ext.get('email'):
		profile.email_verified = False
		reindex_email_verification(user)
		set_email_verification_time(user, 0)
