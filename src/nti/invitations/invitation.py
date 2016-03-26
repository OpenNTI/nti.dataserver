#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.event import notify

from zope.container.contained import Contained

from nti.dataserver_core.interfaces import ICommunity
from nti.dataserver_core.interfaces import IFriendsList
from nti.dataserver_core.interfaces import SYSTEM_USER_NAME

from nti.dublincore.datastructures import CreatedModDateTrackingObject

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationActor
from nti.invitations.interfaces import IInvitationEntityFinder
from nti.invitations.interfaces import InvitationAcceptedEvent
from nti.invitations.interfaces import IJoinEntitiesInvitation
from nti.invitations.interfaces import IInvitationAssociationActor

from nti.zodb.persistentproperty import PersistentPropertyHolder

@interface.implementer(IInvitation, IAttributeAnnotatable)
class BaseInvitation(CreatedModDateTrackingObject, Contained):
	"""
	Starting implementation for an interface that doesn't actually do anything.
	"""

	code = None

	def accept(self, user):
		"""
		This implementation simply broadcasts the accept event.
		"""
		if not user:
			raise ValueError()
		notify(InvitationAcceptedEvent(self, user))

class PersistentInvitation(BaseInvitation, PersistentPropertyHolder):
	""" Invitation meant to be stored persistently. """

class ZcmlInvitation(BaseInvitation):
	"""
	Invitation not intended to be stored persistently, so it won't get intids
	and isn't automatically adaptable to IKeyReference.
	"""

class ActorZcmlInvitation(ZcmlInvitation):
	actor_interface = IInvitationActor

@interface.implementer(IInvitationAssociationActor)
class InvitationAssociationActor(object):
	
	def accept(self, user, entity):
		result = True
		if ICommunity.providedBy(entity):
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

@interface.implementer(IJoinEntitiesInvitation)
class JoinEntitiesInvitation(ActorZcmlInvitation):
	"""
	Simple first pass at a pre-configured invitation to join existing
	entities. Intended to be configured with ZCML and not stored persistently.
	"""

	creator = SYSTEM_USER_NAME
	actor_interface = IInvitationAssociationActor

	def __init__(self, code, entities):
		super(JoinEntitiesInvitation, self).__init__()
		self.code = code
		self.entities = entities

	def transform(self, entity):
		finder = component.getUtility(IInvitationEntityFinder)
		result = finder.find(entity)
		if result is None:
			logger.warn("Unable to accept invitation to join non-existent entity %s",
						entity)
		return result

	def accept(self, user):
		result = False
		actor = component.getUtility(self.actor_interface)
		for entity in self.entities:
			entity = self.transform(entity)
			if entity is not None:
				result = actor.accept(user, entity) or result
		super(JoinEntitiesInvitation, self).accept(user)
		return result

JoinCommunityInvitation = JoinEntitiesInvitation
