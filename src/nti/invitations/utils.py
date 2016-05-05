#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time
from datetime import datetime

from zope import component

from zope.event import notify

from zope.intid.interfaces import IIntIds

from BTrees.LFBTree import LFSet

from nti.invitations.index import IX_ACCEPTED
from nti.invitations.index import IX_RECEIVER
from nti.invitations.index import IX_EXPIRYTIME

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationActor
from nti.invitations.interfaces import InvitationActorError
from nti.invitations.interfaces import InvitationExpiredError
from nti.invitations.interfaces import InvitationAcceptedEvent

from nti.invitations.index import get_invitations_catalog

MAX_TS = time.mktime(datetime.max.timetuple())

def get_invitation_actor(invitation, user=None):
	actor = component.queryMultiAdapter((invitation, user), IInvitationActor)
	if actor is None:
		actor = IInvitationActor(invitation, None)
	return actor
		
def get_pending_invitation_ids(receivers, catalog=None):
	if isinstance(receivers, six.string_types):
		receivers = set(receivers.split(","))
	else:
		receivers = set(receivers)
	catalog = get_invitations_catalog() if catalog is None else catalog
	query = {
		IX_ACCEPTED: {'any_of': (False,)},
		IX_RECEIVER: {'any_of': receivers},
		IX_EXPIRYTIME: {'any_of': (0,)},
	}
	no_expire_ids = catalog.apply(query) or LFSet()
	
	query[IX_EXPIRYTIME] = {'between': (time.time(), MAX_TS)}
	in_between_ids = catalog.apply(query) or LFSet()
	
	result = catalog.family.IF.multiunion([no_expire_ids, in_between_ids])
	return result

def get_pending_invitations(receivers, catalog=None):
	result = []
	intids = component.getUtility(IIntIds)
	doc_ids = get_pending_invitation_ids(receivers, catalog)
	for uid in doc_ids or ():
		obj = intids.queryObject(uid)
		if IInvitation.providedBy(obj):
			result.append(obj)
	return result

def accept_invitation(user, invitation):
	if invitation.is_expired():
		raise InvitationExpiredError(invitation)
	actor = get_invitation_actor(invitation, user)
	if actor is None:
		raise InvitationActorError(invitation)
	if actor.accept(user, invitation):
		notify(InvitationAcceptedEvent(invitation, user))
		return True
	return False
