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
from nti.invitations.index import get_invitations_catalog

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationActor
from nti.invitations.interfaces import InvitationActorError
from nti.invitations.interfaces import InvitationExpiredError
from nti.invitations.interfaces import InvitationAcceptedEvent

MAX_TS = time.mktime(datetime.max.timetuple())

def get_invitation_actor(invitation, user=None):
	actor = component.queryMultiAdapter((invitation, user), IInvitationActor)
	if actor is None:
		actor = IInvitationActor(invitation, None)
	return actor
		
def get_pending_invitation_ids(receivers=None, now=None, catalog=None):
	if isinstance(receivers, six.string_types):
		receivers = set(receivers.split(","))
	elif receivers:
		receivers = set(receivers)
	catalog = get_invitations_catalog() if catalog is None else catalog
	query = {
		IX_ACCEPTED: {'any_of': (False,)},
		IX_EXPIRYTIME: {'any_of': (0,)},
	}
	if receivers:
		receivers.discard(None)
		query[IX_RECEIVER]= {'any_of': receivers}

	# pending no expiry
	no_expire_ids = catalog.apply(query) or LFSet()
	
	# peding with expiration
	now = time.time() if not now else now
	query[IX_EXPIRYTIME] = {'between': (now, MAX_TS)}
	in_between_ids = catalog.apply(query) or LFSet()
	
	result = catalog.family.IF.multiunion([no_expire_ids, in_between_ids])
	return result

def get_pending_invitations(receivers=None, now=None, catalog=None):
	result = []
	intids = component.getUtility(IIntIds)
	doc_ids = get_pending_invitation_ids(receivers, now, catalog)
	for uid in doc_ids or ():
		obj = intids.queryObject(uid)
		if IInvitation.providedBy(obj):
			result.append(obj)
	return result

def get_expired_invitation_ids(receivers=None, now=None, catalog=None):
	if isinstance(receivers, six.string_types):
		receivers = set(receivers.split(","))
	elif receivers:
		receivers = set(receivers)
	now = time.time() - 60 if not now else now # 60 min value w/ minute resolution
	catalog = get_invitations_catalog() if catalog is None else catalog
	query = {
		IX_ACCEPTED: {'any_of': (False,)},
		IX_EXPIRYTIME: {'between': (60, now)}, # 60 min value w/ minute resolution
	}
	if receivers:
		receivers.discard(None)
		query[IX_RECEIVER]= {'any_of': receivers}
	expired_ids = catalog.apply(query) or LFSet()
	return expired_ids

def get_expired_invitations(receivers=None, now=None, catalog=None):
	result = []
	intids = component.getUtility(IIntIds)
	doc_ids = get_expired_invitation_ids(receivers, now, catalog)
	for uid in doc_ids or ():
		obj = intids.queryObject(uid)
		if IInvitation.providedBy(obj):
			result.append(obj)
	return result

def delete_expired_invitations(container, receivers=None, now=None, catalog=None):
	result = []
	invitations = get_expired_invitations(receivers, now, catalog)
	for invitation in invitations:
		if container.remove(invitation):
			result.append(invitation)
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
