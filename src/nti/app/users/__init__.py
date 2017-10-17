#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function,  absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

REL_MY_MEMBERSHIP = 'my_membership'
SUGGESTED_CONTACTS = 'SuggestedContacts'
VERIFY_USER_EMAIL_VIEW = "verify_user_email"
VIEW_USER_UPSERT = "UserUpsert"
VIEW_GRANT_USER_ACCESS = "GrantAccess"
VIEW_RESTRICT_USER_ACCESS = "RemoveAccess"
REQUEST_EMAIL_VERFICATION_VIEW = "request_email_verification"
SEND_USER_EMAIL_VERFICATION_VIEW = "send_user_email_verification"
VERIFY_USER_EMAIL_WITH_TOKEN_VIEW = "verify_user_email_with_token"
