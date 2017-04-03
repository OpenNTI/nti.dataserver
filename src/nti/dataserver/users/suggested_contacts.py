#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import total_ordering

from zope import interface

from zope.container.contained import Contained

from ZODB.utils import u64

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IEntityContainer
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import ISuggestedContact
from nti.dataserver.users.interfaces import ISuggestedContactsProvider
from nti.dataserver.users.interfaces import ISuggestedContactRankingPolicy
from nti.dataserver.users.interfaces import ISecondOrderSuggestedContactProvider

from nti.externalization.representation import WithRepr

from nti.schema.eqhash import EqHash

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties


@total_ordering
@WithRepr
@EqHash("username", "rank")
@interface.implementer(ISuggestedContact)
class SuggestedContact(SchemaConfigured, Contained):
    createDirectFieldProperties(ISuggestedContact)

    @property
    def provider(self):
        return self.__dict__.get('_v_provider')

    @provider.setter
    def provider(self, nv):
        self.__dict__['_v_provider'] = nv

    def __lt__(self, other):
        try:
            return (self.rank, self.username) < (other.rank, other.username)
        except AttributeError:
            return NotImplemented

    def __gt__(self, other):
        try:
            return (self.rank, self.username) > (other.rank, other.username)
        except AttributeError:
            return NotImplemented


@interface.implementer(ISuggestedContactRankingPolicy)
class SuggestedContactRankingPolicy(SchemaConfigured, Contained):
    createDirectFieldProperties(ISuggestedContactRankingPolicy)

    @classmethod
    def sort(cls, contacts):
        contacts = contacts or ()
        return sorted(contacts, reverse=True)


DefaultSuggestedContactRankingPolicy = SuggestedContactRankingPolicy


@interface.implementer(ISuggestedContactRankingPolicy)
class NoOpSuggestedContactRankingPolicy(SchemaConfigured, Contained):
    createDirectFieldProperties(ISuggestedContactRankingPolicy)

    @classmethod
    def sort(cls, contacts):
        return contacts


@interface.implementer(ISuggestedContactsProvider)
class DefaultSuggestedContactsProvider(SchemaConfigured, Contained):
    createDirectFieldProperties(ISuggestedContactsProvider)

    @property
    def priority(self):
        result = getattr(self.ranking, 'priority', None) or 1
        return result

    def suggestions(self, user, source_user=None):
        raise NotImplementedError()
SuggestedContactsProvider = DefaultSuggestedContactsProvider


@interface.implementer(ISecondOrderSuggestedContactProvider)
class _SecondOrderContactProvider(object):
    """
    For the given user, return the best second order contacts.
    This is pretty cheap to do in-memory, for now.
    """

    def __init__(self):
        self.ranking = SuggestedContactRankingPolicy()
        self.ranking.provider = self

    @classmethod
    def _make_visibility_test(cls, user):
        """
        For a given user, create a lambda that excludes those users
        not visible from our user's communities. We also exclude
        `nextthought.com` users.
        """
        if user:
            user_community_names = user.usernames_of_dynamic_memberships - \
                                   set(('Everyone',))

            def test(x):
                try:
                    username = getattr(x, 'username')
                except KeyError:  # pragma: no cover
                    # typically POSKeyError
                    logger.warning("Failed to filter entity with id %s", 
                                   hex(u64(x._p_oid)))
                    return False

                # No one can see the Koppa Kids or nextthought users.
                if     ICoppaUserWithoutAgreement.providedBy(x) \
                    or username.endswith('@nextthought.com'):
                    return False

                # public comms can be searched
                if ICommunity.providedBy(x) and x.public:
                    return True

                # User can see dynamic memberships he's a member of
                # or owns. First, the general case
                container = IEntityContainer(x, None)
                if container is not None:
                    return user in container or getattr(x, 'creator', None) is user

                # Otherwise, visible if it doesn't have dynamic memberships,
                # or we share dynamic memberships
                return not hasattr(x, 'usernames_of_dynamic_memberships') \
                    or x.usernames_of_dynamic_memberships.intersection(user_community_names)
            return test
        return lambda _: True

    def _get_contacts(self, target, accum):
        entities_followed = getattr(target, 'entities_followed', ())
        for entity in entities_followed:
            username = entity.username
            if username in accum:
                suggested_contact = accum[username]
                suggested_contact.rank += 1
            else:
                accum[username] = SuggestedContact(username=username, rank=1)

    def _get_suggestions_for_user(self, user):
        """
        Pull all second order contacts for a user and rank them
        according to frequency.
        """
        accum = dict()
        for target in user.entities_followed:
            self._get_contacts(target, accum)

        existing_pool = {e.username for e in user.entities_followed}
        existing_pool.add(user.username)
        contacts = self.ranking.sort(accum.values())
        return contacts

    def suggestions(self, user, source_user=None):
        # Could we ever come across cross-site suggestions?
        accept_filter = self._make_visibility_test(user)
        existing_pool = {e.username for e in user.entities_followed}
        existing_pool.add(user.username)

        if source_user is not None and user != source_user:
            # Ok, we want suggestions for a user based on a
            # another user. Add that user's friends.
            contacts_iter = tuple(source_user.entities_followed)
            existing_pool.add(source_user.username)
        else:
            # Suggestions based on just our given user.
            contacts_iter = self._get_suggestions_for_user(user)

        for contact in contacts_iter:
            target_name = contact.username
            if target_name not in existing_pool:
                target = User.get_user(target_name)
                if      target is not None \
                    and accept_filter(target):
                    yield target
