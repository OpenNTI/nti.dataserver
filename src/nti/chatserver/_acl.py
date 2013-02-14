#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to ACL implementations for objects in this package.
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

from zope import component

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.authorization_acl import AbstractCreatedAndSharedACLProvider
from nti.dataserver.authorization_acl import ace_allowing

@component.adapter(chat_interfaces.IMeeting)
class _MeetingACLProvider(AbstractCreatedAndSharedACLProvider):
	"""
	Provides the ACL for a meeting: the creator has full access, the current occupants have
	read access, and historical occupants are allowed to re-enter.
	"""

	_DENY_ALL = True

	def _get_sharing_target_names(self):
		return self.context.occupant_names

	def _extend_acl_before_deny( self, acl ):

		for occupant_name in self.context.historical_occupant_names:
			acl.append( ace_allowing( occupant_name, chat_interfaces.ACT_ENTER, _MeetingACLProvider ) )
