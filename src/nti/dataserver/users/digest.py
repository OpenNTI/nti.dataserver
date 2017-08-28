#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from zc.intid.interfaces import IBeforeIdRemovedEvent

import BTrees

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserDigestEmailMetadata

from nti.property.property import annotation_alias

_DIGEST_META_KEY = 'nti.dataserver.users.UsersDigestEmailMetadata'


def _get_family():
    intids = component.queryUtility(IIntIds)
    return getattr(intids, 'family', None) or BTrees.family64


def _storage():
    return _get_family().IO.LOBTree()


@component.adapter(IUser)
@interface.implementer(IUserDigestEmailMetadata)
class _UserDigestEmailMetadata(object):
    """
    Holds digest email user metadata times.
    """

    def __init__(self, user):
        self.parent = user.__parent__
        self.user_key = self._get_user_key(user)

    def _get_user_key(self, user):
        intids = component.getUtility(IIntIds)
        user_intid = intids.getId(user)
        return user_intid

    _user_meta_storage = annotation_alias(_DIGEST_META_KEY,
                                          annotation_property='parent',
                                          doc=u"The time metadata storage on the users folder")

    def _get_meta_storage(self):
        if self._user_meta_storage is None:
            self._user_meta_storage = _storage()
        return self._user_meta_storage

    def _get_last_collected(self):
        # last_collected is index 0
        meta_storage = self._get_meta_storage()
        try:
            result = meta_storage[self.user_key]
            result = result[0]
        except KeyError:
            result = 0
        return result

    def _set_last_collected(self, update_time):
        meta_storage = self._get_meta_storage()
        try:
            user_data = meta_storage[self.user_key]
            user_data = (update_time, user_data[1])
        except KeyError:
            user_data = (update_time, 0)
        meta_storage[self.user_key] = user_data

    def _get_last_sent(self):
        # last_sent is index 1
        meta_storage = self._get_meta_storage()
        try:
            result = meta_storage[self.user_key]
            result = result[1]
        except KeyError:
            result = 0
        return result

    def _set_last_sent(self, update_time):
        meta_storage = self._get_meta_storage()
        try:
            user_data = meta_storage[self.user_key]
            user_data = (user_data[0], update_time)
        except KeyError:
            user_data = (0, update_time)
        meta_storage[self.user_key] = user_data

    last_sent = property(_get_last_sent, _set_last_sent)
    last_collected = property(_get_last_collected, _set_last_collected)

    def remove_user_data(self):
        meta_storage = self._get_meta_storage()
        try:
            del meta_storage[self.user_key]
        except KeyError:
            pass

    def __len__(self):
        return 0 if not self._user_meta_storage else len(self._user_meta_storage)

    def __bool__(self):
        return True
    __nonzero__ = __bool__


@component.adapter(IUser, IBeforeIdRemovedEvent)
def _digest_email_remove_user(user, unused_event):
    user_metadata = IUserDigestEmailMetadata(user)
    user_metadata.remove_user_data()
