#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of the :class:`nti.appserver.invitations.interfaces.IInvitation` interface.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import persistent

from zope import interface

from zope.container import contained
from zope.event import notify

from zope.annotation import interfaces as an_interfaces
from . import interfaces as invite_interfaces
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver import datastructures
from nti.dataserver import users

@interface.implementer(invite_interfaces.IInvitation, an_interfaces.IAttributeAnnotatable)
class BaseInvitation(datastructures.CreatedModDateTrackingObject,contained.Contained):
	"""
	Starting implementation for an interface that doesn't actually do anything.
	"""

	code = None

	def accept( self, user ):
		"""
		This implementation simply broadcasts the accept event.
		"""
		if not user: raise ValueError()
		notify( invite_interfaces.InvitationAcceptedEvent( self, user ) )


class PersistentInvitation(persistent.Persistent,BaseInvitation):
	""" Invitation meant to be stored persistently. """


class ZcmlInvitation(BaseInvitation):
	"""
	Invitation not intended to be stored persistently, so it won't get intids
	and isn't automatically adaptable to IKeyReference.
	"""

class JoinCommunityInvitation(ZcmlInvitation):
	"""
	Simple first pass at a pre-configured invitation to join existing
	entities. Intended to be configured with ZCML and not stored persistently.
	"""

	creator = nti_interfaces.SYSTEM_USER_NAME

	def __init__( self, code, entities ):
		super(JoinCommunityInvitation,self).__init__()
		self.code = code
		self.entities = entities

	def accept( self, user ):
		for entity_name in self.entities:
			entity = users.Entity.get_entity( entity_name )
			if entity is None:
				logger.warn( "Unable to accept invitation to join non-existent entity %s", entity_name )
				continue
			if nti_interfaces.ICommunity.providedBy( entity ):
				logger.info( "Accepting invitation to join community %s", entity )
				user.join_community( entity )
				user.follow( entity )
			elif nti_interfaces.IFriendsList.providedBy( entity ):
				logger.info( "Accepting invitation to join DFL %s", entity )
				entity.addFriend( user )
			else:
				logger.warn( "Don't know how to accept invitation to join entity %s", entity )
		super(JoinCommunityInvitation,self).accept( user )
