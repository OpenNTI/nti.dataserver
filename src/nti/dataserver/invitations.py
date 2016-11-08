#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import IJoinEntityInvitation
from nti.dataserver.interfaces import IJoinEntityInvitationActor

from nti.dataserver.users import Entity

from nti.invitations.model import Invitation

from nti.schema.fieldproperty import createDirectFieldProperties

@interface.implementer(IJoinEntityInvitation)
class JoinEntityInvitation(Invitation):
	createDirectFieldProperties(IJoinEntityInvitation)

	mimeType = mime_type = u"application/vnd.nextthought.joinentityinvitation"

JoinCommunityInvitation = JoinEntityInvitation

@interface.implementer(IJoinEntityInvitationActor)
class JoinEntityInvitationActor(object):

	def __init__(self, invitation=None):
		self.invitation = invitation

	def accept(self, user, invitation=None):
		result = True
		invitation = self.invitation if invitation is None else invitation
		entity = Entity.get_entity(invitation.entity)
		if entity is None:
			logger.warn("Entity %s does not exists", invitation.entity)
			result = False
		elif ICommunity.providedBy(entity):
			logger.info("Accepting invitation to join community %s", entity)
			user.record_dynamic_membership(entity)
			user.follow(entity)
		elif IFriendsList.providedBy(entity):
			logger.info("Accepting invitation to join DFL %s", entity)
			entity.addFriend(user)
		else:
			result = False
			logger.warn("Don't know how to accept invitation to join entity %s",
						entity)
		return result
