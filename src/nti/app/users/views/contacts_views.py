#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from requests.structures import CaseInsensitiveDict

from zope import component

from zope.security.interfaces import IPrincipal

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.users import SUGGESTED_CONTACTS

from nti.dataserver.authorization import ACT_READ

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IHiddenMembership
from nti.dataserver.users.interfaces import IDisallowSuggestedContacts
from nti.dataserver.users.interfaces import get_all_suggested_contacts
from nti.dataserver.users.interfaces import ISecondOrderSuggestedContactProvider

from nti.dataserver.users.suggested_contacts import SuggestedContact

from nti.externalization.externalization import toExternalObject

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

CLASS = StandardExternalFields.CLASS
ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
MIMETYPE = StandardExternalFields.MIMETYPE
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

SUGGESTED_CONTACTS_MIMETYPE = 'application/vnd.nextthought.suggestedcontacts'


def to_suggested_contacts(users):
    result = []
    for user in users or ():
        principal = IPrincipal(user)
        contact = SuggestedContact(username=principal.id, rank=1)
        result.append(contact)
    return result


class _AbstractSuggestedContactsView(AbstractAuthenticatedView):

    #: The maximum number of results we will return
    MAX_REQUEST_SIZE = 10

    #: The minimum number of results we must return
    MIN_RESULT_COUNT = 4

    def _get_params(self):
        params = CaseInsensitiveDict(self.request.params)
        self.result_count = params.get('Count') or self.MAX_REQUEST_SIZE
        if self.result_count > self.MAX_REQUEST_SIZE:
            self.result_count = self.MAX_REQUEST_SIZE
        self.existing_pool = {
            x.username for x in self.remoteUser.entities_followed
        }
        self.existing_pool.add(self.remoteUser.username)


@view_config(route_name='objects.generic.traversal',
             name=SUGGESTED_CONTACTS,
             request_method='GET',
             permission=ACT_READ,
             context=IUser)
class UserSuggestedContactsView(_AbstractSuggestedContactsView):
    """
    For the contextual user, return suggested contacts based on:

            1. Friends friends list (2nd order)
            2. Suggested contacts utility
    """
    #: The portion of results we get from our contact pool.
    LIMITED_CONTACT_RATIO = .6

    #: The portion of results we get from the context.
    LIMITED_CONTACT_RATIO_SINGLE_SOURCE = .2

    #: The minimum number of contacts we must have in our pool
    MIN_LIMITED_CONTACT_POOL_SIZE = 2

    #: The minimum number of contacts our context must have.
    #: For a user with 5 friends, we'll return a single contact
    #: from that source. Less than that and we'll return nothing.
    MIN_LIMITED_CONTACT_POOL_SIZE_SINGLE_SOURCE = 5

    #: XXX: Do we need a min fill count to preserve privacy?
    #: The minimum number of filled in suggestions that may help
    #: maintain privacy.
    MIN_FILL_COUNT = 0

    def _set_limited_count(self, pool, pool_size_min, limited_ratio):
        self.limited_count = 0
        # Only fetch from our limited contacts if our pool size is
        # large enough.
        if len(pool) >= pool_size_min:
            limited_count = limited_ratio * self.result_count
            self.limited_count = int(limited_count)

    def _get_params(self):
        super(UserSuggestedContactsView, self)._get_params()
        # We want to not return the context the user is looking at.
        self.existing_pool.add(self.context.username)
        if self.remoteUser == self.context:
            self._set_limited_count(self.existing_pool,
                                    self.MIN_LIMITED_CONTACT_POOL_SIZE,
                                    self.LIMITED_CONTACT_RATIO)
        else:
            self._set_limited_count(tuple(self.context.entities_followed),
                                    self.MIN_LIMITED_CONTACT_POOL_SIZE_SINGLE_SOURCE,
                                    self.LIMITED_CONTACT_RATIO_SINGLE_SOURCE)

    def _get_suggestion_args(self):
        """
        We are fetching suggested contacts for a user, or for
        a user based on another user.
        """
        if self.remoteUser == self.context:
            results = (self.remoteUser,)
        else:
            results = (self.remoteUser, self.context)
        return results

    def _get_limited_contacts(self):
        """
        Get our prioritized contacts from our friends.
        """
        if not self.existing_pool or not self.limited_count:
            return ()
        results = set()
        suggestion_args = self._get_suggestion_args()
        for _, provider in component.getUtilitiesFor(ISecondOrderSuggestedContactProvider):
            for suggestion in provider.suggestions(*suggestion_args):
                results.add(suggestion)
                if len(results) >= self.limited_count:
                    break
        return results

    def _get_fill_in_contacts(self, intermediate_contacts):
        """
        Get the rest of our suggested contacts from our contacts
        utility.
        """
        # TODO: Currently our only subscriber does so based on
        # courses.  We also need one for global community.
        results = set()
        fill_in_count = self.result_count - len(intermediate_contacts)
        intermediate_usernames = {x.username for x in intermediate_contacts}
        for contact in get_all_suggested_contacts(self.context):
            if         contact.username not in intermediate_usernames \
                and contact.username not in self.existing_pool \
                and not contact.username.endswith('@nextthought.com'):
                contact = User.get_user(contact.username)
                if contact:
                    results.add(contact)
                    if len(results) >= fill_in_count:
                        break
        return results

    def __call__(self):
        if self.remoteUser is None:
            raise hexc.HTTPForbidden()
        results = LocatedExternalDict()
        self._get_params()
        limited_contacts = self._get_limited_contacts()
        fill_in_contacts = self._get_fill_in_contacts(limited_contacts)
        results[TOTAL] = results[ITEM_COUNT] = 0
        results[CLASS] = SUGGESTED_CONTACTS
        results[MIMETYPE] = SUGGESTED_CONTACTS_MIMETYPE
        # Only return anything if we meet our minimum requirements.
        if         len(fill_in_contacts) >= self.MIN_FILL_COUNT \
            and len(limited_contacts) + len(fill_in_contacts) >= self.MIN_RESULT_COUNT:
            result_list = []
            result_list.extend(limited_contacts)
            result_list.extend(fill_in_contacts)
            results[ITEMS] = [toExternalObject(
                x, name="summary") for x in result_list]
            results[TOTAL] = results[ITEM_COUNT] = len(result_list)
        return results


@view_config(context=ICommunity)
@view_config(context=IDynamicSharingTargetFriendsList)
@view_config(route_name='objects.generic.traversal',
             name=SUGGESTED_CONTACTS,
             permission=ACT_READ,
             request_method='GET')
class _MembershipSuggestedContactsView(_AbstractSuggestedContactsView):
    """
    Simple contact suggestions based on members of
    context.
    """

    def _accept_filter(self, member, hidden):
        """
        Only add new, non-hidden, non-nextthought users.
        """
        return IUser.providedBy(member) \
           and member.username not in self.existing_pool \
           and not member.username.endswith('@nextthought.com') \
           and not member in hidden

    def _get_contacts(self):
        results = set()
        creator = self.context.creator
        creator_username = getattr(creator, 'username', creator)
        hidden = IHiddenMembership(self.context, None) or ()
        if creator and creator_username not in self.existing_pool:
            results.add(creator)
        for member in self.context:
            if self._accept_filter(member, hidden):
                results.add(member)
                if len(results) >= self.result_count:
                    break
        return results

    def __call__(self):
        context = self.context
        # Should we check for public here? It's false by default.
        # is_public = context.public if ICommunity.providedBy( context ) else True

        if     self.remoteUser is None \
            or IDisallowSuggestedContacts.providedBy(context) \
            or not (   self.remoteUser in context
                    or self.remoteUser == context.creator):
            raise hexc.HTTPForbidden()

        results = LocatedExternalDict()
        self._get_params()
        contacts = self._get_contacts()
        results[TOTAL] = results[ITEM_COUNT] = 0
        results[CLASS] = SUGGESTED_CONTACTS
        results[MIMETYPE] = SUGGESTED_CONTACTS_MIMETYPE
        if len(contacts) >= self.MIN_RESULT_COUNT:
            result_list = []
            result_list.extend(contacts)
            results[ITEMS] = [
                toExternalObject(x, name="summary") for x in result_list
            ]
            results[TOTAL] = results[ITEM_COUNT] = len(result_list)
        return results
