#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations related to :class:`IContacts.`

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from .interfaces import IContacts
from nti.dataserver.interfaces import IUser

from nti.utils.property import alias

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
		has_me_in_buddy_list = {e.username for e in self.context.entities_followed} | set(self.context.accepting_shared_data_from)
		return has_me_in_buddy_list

	@property
	def contactNamesISubscribeToPresenceUpdates(self):
		return self.contactNamesSubscribedToMyPresenceUpdates
