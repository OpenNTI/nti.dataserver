#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time
import BTrees

from zope import component
from zope import interface

from zope.location.interfaces import IContained

from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from persistent.persistence import Persistent

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users.interfaces import IRecreatableUser

from nti.zodb.containers import time_to_64bit_int

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IContained)
@interface.implementer(IUserBlacklistedStorage)
class UserBlacklistedStorage(Persistent):
    """
    Stores deleted/blacklisted usernames case-insensitively in a btree
    to their int-encoded delete times.
    """

    __name__ = None
    __parent__ = None

    def __init__(self):
        self._storage = BTrees.OLBTree.BTree()

    def _get_user_key(self, user):
        username = getattr(user, 'username', user)
        return username.lower()

    def blacklist_user(self, user):
        now = time.time()
        user_key = self._get_user_key(user)
        self._storage[user_key] = time_to_64bit_int(now)
    add = blacklist_user

    def is_user_blacklisted(self, user):
        user_key = self._get_user_key(user)
        return user_key in self._storage
    __contains__ = is_user_blacklisted

    def remove_blacklist_for_user(self, username):
        result = False
        try:
            del self._storage[username]
            result = True
        except KeyError:
            pass
        return result
    remove = remove_blacklist_for_user

    def clear(self):
        self._storage.clear()
    reset = clear

    def __iter__(self):
        return iter(self._storage.items())

    def __len__(self):
        return len(self._storage)


@component.adapter(IUser, IObjectRemovedEvent)
def _on_user_removed(user, unused_event):
    username = user.username
    if 		not IRecreatableUser.providedBy(user) \
        and not username.lower().endswith('@nextthought.com'):
        user_blacklist = component.getUtility(IUserBlacklistedStorage)
        user_blacklist.blacklist_user(user)
        logger.info("Black-listing username %s", username)
