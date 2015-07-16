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

from zope import component

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout

REL_MY_MEMBERSHIP = 'my_membership'
SUGGESTED_CONTACTS = 'SuggestedContacts'
VERIFY_USER_EMAIL_VIEW = "verify_user_email"
REQUEST_EMAIL_VERFICATION_VIEW = "request_email_verification"
SEND_USER_EMAIL_VERFICATION_VIEW = "send_user_email_verification"
VERIFY_USER_EMAIL_WITH_TOKEN_VIEW = "verify_user_email_with_token"

def is_true(value):
	value = value if isinstance(value, six.string_types) else str(value)
	return value.lower() in ('1', 'y', 'yes', 't', 'true')

def _make_min_max_btree_range(search_term):
	min_inclusive = search_term  # start here
	max_exclusive = search_term[0:-1] + unichr(ord(search_term[-1]) + 1)
	return min_inclusive, max_exclusive

def username_search(search_term):
	min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
	dataserver = component.getUtility(IDataserver)
	_users = IShardLayout(dataserver).users_folder
	usernames = list(_users.iterkeys(min_inclusive, max_exclusive, excludemax=True))
	return usernames

def all_usernames():
	dataserver = component.getUtility(IDataserver)
	users_folder = IShardLayout(dataserver).users_folder
	usernames = users_folder.keys()
	return usernames
