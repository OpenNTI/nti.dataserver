#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations related to :class:`IContacts.`

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.event import notify

from nti.chatserver.interfaces import IContacts
from nti.chatserver.interfaces import ContactISubscribeToAddedToContactsEvent

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IFollowerAddedEvent

from nti.externalization.persistence import NoPickle

from nti.property.property import alias

logger = __import__('logging').getLogger(__name__)


@NoPickle
@component.adapter(IUser)
@interface.implementer(IContacts)
class DefaultComputedContacts(object):
    """
    Dynamically computes the contact list for the user
    based on deriving information from his other fields.
    """

    __parent__ = alias('context')

    def __init__(self, context):
        self.context = context

    @property
    def contactNamesSubscribedToMyPresenceUpdates(self):
        # Better algorithm. Who should this really go to?
        followed = {e.username for e in self.context.entities_followed}
        shared_from = set(self.context.accepting_shared_data_from)
        has_me_in_buddy_list = followed | shared_from
        return has_me_in_buddy_list

    @property
    def contactNamesISubscribeToPresenceUpdates(self):
        return self.contactNamesSubscribedToMyPresenceUpdates


@component.adapter(IUser, IFollowerAddedEvent)
def default_computed_contacts_change_when_follower_added(user_being_followed, event):
    """
    When a follower is added to a user, that follower's default contacts change.
    """
    user_now_following = event.followed_by
    if      IUser.providedBy(user_now_following) \
        and IUser.providedBy(user_being_followed):
        notify(ContactISubscribeToAddedToContactsEvent(user_now_following,
                                                       user_being_followed))
