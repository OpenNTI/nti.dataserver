#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to ACL implementations for objects in this package.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from nti.chatserver.interfaces import ACT_ENTER

from nti.chatserver.interfaces import IMeeting

from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ACT_NTI_ADMIN 

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import AbstractCreatedAndSharedACLProvider

logger = __import__('logging').getLogger(__name__)


@component.adapter(IMeeting)
class _MeetingACLProvider(AbstractCreatedAndSharedACLProvider):
    """
    Provides the ACL for a meeting: the creator has full access, the current occupants
    have read access, and historical occupants are allowed to re-enter.
    """

    _DENY_ALL = True

    def _get_sharing_target_names(self):
        return self.context.occupant_names

    def _extend_acl_after_creator_and_sharing(self, acl):
        # so admins can administer (e.g. delete)
        acl.append(ace_allowing(ROLE_ADMIN, ACT_NTI_ADMIN, type(self)))

    def _extend_acl_before_deny(self, acl):
        for occupant_name in self.context.historical_occupant_names or ():
            acl.append(ace_allowing(occupant_name, ACT_ENTER, type(self)))
