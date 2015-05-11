#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of the :class:`nti.appserver.invitations.interfaces.IInvitation` interface.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.event import notify

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.container.contained import Contained

from nti.dataserver import users
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import SYSTEM_USER_NAME

from nti.dublincore.datastructures import CreatedModDateTrackingObject
from nti.zodb.persistentproperty import PersistentPropertyHolder

from .interfaces import IInvitation
from .interfaces import InvitationAcceptedEvent

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

class JoinEntitiesInvitation(ZcmlInvitation):
	"""
	Simple first pass at a pre-configured invitation to join existing
	entities. Intended to be configured with ZCML and not stored persistently.
	"""

	creator = SYSTEM_USER_NAME

	def __init__(self, code, entities):
		super(JoinEntitiesInvitation, self).__init__()
		self.code = code
		self.entities = entities

	def _iter_entities(self):
		for entity_name in self.entities:
			entity = users.Entity.get_entity( entity_name )
			if entity is None:
				logger.warn("Unable to accept invitation to join non-existent entity %s", entity_name)
				continue
			yield entity

	def accept(self, user):
		for entity in self._iter_entities():
			if ICommunity.providedBy( entity ):
				logger.info("Accepting invitation to join community %s", entity)
				user.record_dynamic_membership(entity)
				user.follow(entity)
			elif IFriendsList.providedBy(entity):
				logger.info("Accepting invitation to join DFL %s", entity)
				entity.addFriend(user)
			else:
				logger.warn("Don't know how to accept invitation to join entity %s", entity)
		super(JoinEntitiesInvitation, self).accept(user)

JoinCommunityInvitation = JoinEntitiesInvitation
