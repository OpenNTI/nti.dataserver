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

from nti.coremetadata.interfaces import IEntityContainer
from nti.coremetadata.interfaces import IMentionable
from nti.coremetadata.interfaces import ISharingTargetEntityIterable

from nti.dataserver.interfaces import IMentionsUpdateInfo

from nti.dataserver.mentions.interfaces import IPreviousMentions

from nti.dataserver.users import User

from nti.contentfragments.interfaces import IAllowedAttributeProvider

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


@interface.implementer(IAllowedAttributeProvider)
class _MentionAttributesProvider(object):
    allowed_attributes = frozenset([
        "data-nti-entity-type",
        "data-nti-entity-mutability",
        "data-nti-entity-id",
        "data-nti-entity-username",
    ])


_unset = object()


@interface.implementer(IMentionsUpdateInfo)
class _MentionsUpdateInfo(object):

    def __init__(self, mentionable, old_shares=_unset):
        self.context = mentionable
        self.old_shares = old_shares if old_shares is not _unset else set()

    @Lazy
    def new_effective_mentions(self):
        shared_to = self.mentions_shared_to

        if not self.old_shares:
            return shared_to

        return self._mentions_added_with_existing_perms(shared_to) | shared_to

    def _mentions_at_trans_start(self):
        prev = IPreviousMentions(self.context)

        # If mentions weren't updated in this transaction,
        # get the current mentions
        if not prev.is_modified():
            return self.context.mentions

        return prev.mentions or ()

    @Lazy
    def _mentions_added(self):
        orig_mentions = self._mentions_at_trans_start()

        usernames_added = set(self.context.mentions) - set(orig_mentions)

        users_added = set()
        for username in usernames_added:
            user = User.get_user(username)
            if user is not None:
                users_added.add(user)

        return users_added

    def _mentions_added_with_existing_perms(self, shared_to):
        added_without_share = self._mentions_added - shared_to

        new_permissioned_mentions = set()
        for user in added_without_share:
            if self.context.isSharedWith(user):
                new_permissioned_mentions.add(user)

        return new_permissioned_mentions

    @Lazy
    def mentions_added(self):
        shared_to = self.mentions_shared_to
        return self._mentions_added_with_existing_perms(shared_to)

    def _users_mentioned(self):
        users_mentioned = list()
        for username in self.context.mentions:
            user = User.get_user(username)
            if user is not None:
                users_mentioned.append(user)
        return users_mentioned

    @Lazy
    def mentions_shared_to(self):
        new_shares = set(self.context.sharingTargets) - set(self.old_shares)

        user_shared_to = set()
        if not new_shares:
            return user_shared_to

        # TODO: Could store notified mentions to speed this up
        for user in self._users_mentioned():
            if self._was_shared_to(user, self.old_shares, new_shares):
                user_shared_to.add(user)

        return user_shared_to

    def _was_shared_to(self, user, old_shares, new_shares):
        return self._is_member_of_any(user, new_shares) \
            and not self._is_member_of_any(user, old_shares)

    @staticmethod
    def _is_member_of_any(user, sharing_targets):
        if user in sharing_targets:
            return True

        for target in sharing_targets:
            if user in IEntityContainer(target, ()):
                return True

        return False

