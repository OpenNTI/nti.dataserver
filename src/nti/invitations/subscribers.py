#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationSentEvent

@component.adapter(IInvitation, IInvitationSentEvent)
def _on_invitation_sent(invitation, event):
	invitation.sent = time.time()
