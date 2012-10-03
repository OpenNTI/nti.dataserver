#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of the :class:`nti.appserver.invitations.interfaces.IInvitation` interface.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container import contained
from zope.event import notify

from zope.annotation import interfaces as an_interfaces
from . import interfaces as invite_interfaces

from nti.dataserver import datastructures

@interface.implementer(invite_interfaces.IInvitation, an_interfaces.IAttributeAnnotatable)
class PersistentInvitation(datastructures.PersistentCreatedModDateTrackingObject,contained.Contained):
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
