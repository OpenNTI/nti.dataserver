#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six

from zope import component

from zope.mimetype.interfaces import IContentTypeAware

from nti.app.users import MessageFactory

from nti.app.users import REL_MY_MEMBERSHIP
from nti.app.users import SUGGESTED_CONTACTS
from nti.app.users import VERIFY_USER_EMAIL_VIEW
from nti.app.users import REQUEST_EMAIL_VERFICATION_VIEW
from nti.app.users import SEND_USER_EMAIL_VERFICATION_VIEW
from nti.app.users import VERIFY_USER_EMAIL_WITH_TOKEN_VIEW

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout

logger = __import__('logging').getLogger(__name__)


def _make_min_max_btree_range(search_term):
    min_inclusive = search_term  # start here
    max_exclusive = search_term[0:-1] + six.unichr(ord(search_term[-1]) + 1)
    return min_inclusive, max_exclusive


def username_search(search_term):
    min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
    dataserver = component.getUtility(IDataserver)
    _users = IShardLayout(dataserver).users_folder
    usernames = _users.iterkeys(min_inclusive, max_exclusive, excludemax=True)
    return usernames


def all_usernames():
    dataserver = component.getUtility(IDataserver)
    users_folder = IShardLayout(dataserver).users_folder
    usernames = users_folder.keys()
    return usernames


def parse_mimeType(obj):
    return getattr(obj, 'mimeType', None) or getattr(obj, 'mime_type', None)


def get_mime_type(obj, default='unknown'):
    result = parse_mimeType(obj)
    if not result:
        obj = IContentTypeAware(obj, None)
        result = parse_mimeType(obj)
    return result or default


def parse_mime_types(value):
    mime_types = set(value.split(',')) if value else ()
    if '*/*' in mime_types:
        mime_types = ()
    elif mime_types:
        mime_types = {e.strip().lower() for e in mime_types if e}
        mime_types.discard('')
    return tuple(mime_types) if mime_types else ()
