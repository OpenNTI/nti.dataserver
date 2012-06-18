#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to ACL implementations for objects in this package.
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import component

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver.authorization_acl import AbstractCreatedAndSharedACLProvider

@component.adapter(chat_interfaces.IMeeting)
class _MeetingACLProvider(AbstractCreatedAndSharedACLProvider):
	"""
	Provides the ACL for a meeting: the creator has full access, the occupants have
	read access.
	"""

	def _get_sharing_target_names(self):
		return self._created.occupant_names
