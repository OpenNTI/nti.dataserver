#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to ACL implementations for objects in this package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.chatserver.interfaces import ACT_ENTER

from nti.chatserver.interfaces import IMeeting

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import AbstractCreatedAndSharedACLProvider


@component.adapter(IMeeting)
class _MeetingACLProvider(AbstractCreatedAndSharedACLProvider):
    """
    Provides the ACL for a meeting: the creator has full access, the current occupants
    have read access, and historical occupants are allowed to re-enter.
    """

    _DENY_ALL = True

    def _get_sharing_target_names(self):
        return self.context.occupant_names

    def _extend_acl_before_deny(self, acl):
        for occupant_name in self.context.historical_occupant_names:
            acl.append(ace_allowing(occupant_name, ACT_ENTER, type(self)))
