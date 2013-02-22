# -*- coding: utf-8 -*-
"""
Base class for payment processors.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from nti.appserver.invitations import interfaces as invite_interfaces

from .. import invitations

class _BasePaymentProcessor(object):
	
	def register_invitation(self, purchase_id, username, entities=(), capacity=None):
		utility = component.getUtility( invite_interfaces.IInvitations )
		invitation = invitations.create_store_invitation(purchase_id, username, entities, capacity)
		utility.registerInvitation(invitation)
		return invitation
