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

    def validate_coupon(self, coupon):
        return True

    def apply_coupon(self, amount, coupon=None):
        return amount

    def register_invitation(self, purchase_id, username, capacity=None, entities=()):
        utility = component.getUtility(invite_interfaces.IInvitations)
        invitation = invitations.create_store_invitation(purchase_id, username, capacity, entities)
        utility.registerInvitation(invitation)
        return invitation
