#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.app.base.abstract_views import make_sharing_security_check_for_object

from nti.coremetadata.interfaces import IMentionable
from nti.coremetadata.interfaces import ISharingTargetEntityIterable

from nti.dataserver.users import User

logger = __import__('logging').getLogger(__name__)


def _lower(s):
    return s.lower() if s else s


@component.adapter(IMentionable)
@interface.implementer(ISharingTargetEntityIterable)
class ValidMentionableEntityIterable(object):
    """
    Iterates the usernames from a mentionable and yields
    those users, assuming they're valid entities for a
    mention notification.
    """

    def __init__(self, mentionable):
        self.context = mentionable

    @Lazy
    def _security_check(self):
        return make_sharing_security_check_for_object(self.context)

    @Lazy
    def _creator_username(self):
        creator = getattr(self.context, "creator", None)
        return getattr(creator, "username", creator)

    def _is_creator(self, user):
        return _lower(user.username) == _lower(self._creator_username)

    def _predicate(self, user):
        return user is not None \
            and not self._is_creator(user) \
            and self._security_check(user)

    def __iter__(self):
        for username in self.context.mentions or ():
            user = User.get_user(username)
            if self._predicate(user):
                yield user

