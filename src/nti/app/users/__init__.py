#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

import six

VERIFY_USER_EMAIL_VIEW = "verify_user_email"
REQUEST_EMAIL_VERFICATION_VIEW = "request_email_verification"
SEND_USER_EMAIL_VERFICATION_VIEW = "send_user_email_verification"
VERIFY_USER_EMAIL_WITH_TOKEN_VIEW = "verify_user_email_with_token"

def safestr(s):
    s = s.decode("utf-8") if isinstance(s, bytes) else s
    return unicode(s) if s is not None else None

def is_true(value):
    value = value if isinstance(value, six.string_types) else str(value)
    return value.lower() in ('1', 'y', 'yes', 't', 'true')
