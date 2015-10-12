#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.event import notify

from zope.container.contained import Contained

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

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.app.invitations.invitation",
    "nti.app.invitations.invitation",
    "JoinEntitiesInvitation",
    "JoinCommunityInvitation")
