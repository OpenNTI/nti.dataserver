#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations related to :class:`IContacts.`

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.event import notify

from nti.common.property import alias

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IFollowerAddedEvent

from .interfaces import IContacts
from .interfaces import ContactISubscribeToAddedToContactsEvent

@interface.implementer(IContacts)
@component.adapter(IUser)
class DefaultComputedContacts(object):
	"""
	Dynamically computes the contact list for the user
	based on deriving information from his other fields.
	"""

	def __init__( self, context ):
		self.context = context
	__parent__ = alias('context')

	def __reduce__(self):
		"cannot be pickled; transient"
		raise TypeError()

	@property
	def contactNamesSubscribedToMyPresenceUpdates(self):
		# TODO: Better algorithm. Who should this really go to?
		has_me_in_buddy_list = {e.username for e in self.context.entities_followed} | \
								set(self.context.accepting_shared_data_from)
		return has_me_in_buddy_list

	@property
	def contactNamesISubscribeToPresenceUpdates(self):
		return self.contactNamesSubscribedToMyPresenceUpdates

@component.adapter(IUser, IFollowerAddedEvent)
def default_computed_contacts_change_when_follower_added( user_being_followed, event ):
	"""
	When a follower is added to a user, that follower's default contacts change.
	"""
	user_now_following = event.followed_by
	if IUser.providedBy( user_now_following ) and IUser.providedBy( user_being_followed ):
		notify( ContactISubscribeToAddedToContactsEvent( user_now_following, user_being_followed ) )
