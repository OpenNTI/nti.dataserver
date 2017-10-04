#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from zope import component

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationSentEvent

logger = __import__('logging').getLogger(__name__)


@component.adapter(IInvitation, IInvitationSentEvent)
def _on_invitation_sent(invitation, _):
    invitation.sent = time.time()
