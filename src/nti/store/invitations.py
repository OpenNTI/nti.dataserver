# -*- coding: utf-8 -*-
"""
Store invitations

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zc.intid as zc_intid

from zope import component

from nti.appserver.invitations import interfaces as invite_interfaces
from nti.appserver.invitations.invitation import JoinEntitiesInvitation

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import integer_strings

from . import MessageFactory as _
from .purchase_history import get_purchase_attempt
from ._content_roles import _add_users_content_roles

class InvitationCapacityExceeded(Exception):
	"""
	Raised when a user is attempting to accept an invitation whose capacity has been exceeded.
	"""

	i18n_message = _("The limit for this invitation code has been exceeded.")

class _StoreEntityInvitation(JoinEntitiesInvitation):

	def __init__(self, code, purchase):
		super(_StoreEntityInvitation, self).__init__(code, ())
		self.purchase = purchase

	@property
	def capacity(self):
		return self.purchase.Quantity

	def accept(self, user):
		if self.purchase.consume_token():
			super(_StoreEntityInvitation, self).accept(user)
			_add_users_content_roles(user, self.purchase.Items)
		else:
			raise InvitationCapacityExceeded()

def get_invitation_code(purchase):
	if purchase is not None:
		iid = component.getUtility(zc_intid.IIntIds).getId(purchase)
		result = integer_strings.to_external_string(iid)
	else:
		result = None
	return result

def create_store_invitation(purchase, code=None):
	invitation_code = code if code else get_invitation_code(purchase)
	result = _StoreEntityInvitation(invitation_code, purchase)
	result.creator = purchase.creator
	return result

def register_invitation(purchase_id, username=None):
	utility = component.getUtility(invite_interfaces.IInvitations)
	invitation = create_store_invitation(purchase_id, username)
	utility.registerInvitation(invitation)
	return invitation

def _consume_purchase_token(purchase_id, username=None):
	result = []
	def func():
		purchase = get_purchase_attempt(purchase_id, username)
		result.append(purchase.consume_token())
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	return result[0]
