# -*- coding: utf-8 -*-
"""
Store invitations

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zc.intid as zc_intid

from zope import component
from zope import interface

from nti.appserver.invitations import interfaces as invite_interfaces
from nti.appserver.invitations.invitation import JoinEntitiesInvitation

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization import integer_strings

from . import MessageFactory as _
from . import interfaces as store_interfaces
from ._content_roles import _add_users_content_roles

interface.alsoProvides(store_interfaces.IStorePurchaseInvitation, invite_interfaces.IInvitation)

class InvitationCapacityExceeded(Exception):
	"""
	Raised when a user is attempting to accept an invitation whose capacity has been exceeded.
	"""
	i18n_message = _("The limit for this invitation code has been exceeded.")

class InvitationAlreadyAccepted(Exception):
	"""
	Raised when a user is attempting to accept an invitation more than once
	"""
	i18n_message = _("Invitation already accepted")

@interface.implementer(store_interfaces.IStorePurchaseInvitation)
class _StorePurchaseInvitation(JoinEntitiesInvitation):

	def __init__(self, code, purchase):
		super(_StorePurchaseInvitation, self).__init__(code, ())
		self.purchase = purchase

	@property
	def capacity(self):
		return self.purchase.Quantity

	def accept(self, user):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		if self.purchase.register(user):
			if self.purchase.consume_token():
				super(_StorePurchaseInvitation, self).accept(user)
				_add_users_content_roles(user, self.purchase.Items)
			else:
				raise InvitationCapacityExceeded()
		else:
			raise InvitationAlreadyAccepted()

def get_invitation_code(purchase):
	if purchase is not None:
		iid = component.getUtility(zc_intid.IIntIds).getId(purchase)
		result = integer_strings.to_external_string(iid)
		return result
	return None

def get_purchase_by_code(code):
	if code is not None:
		iid = integer_strings.from_external_string(code)
		result = component.getUtility(zc_intid.IIntIds).queryObject(iid)
		return result
	return None

def create_store_purchase_invitation(purchase, code=None):
	invitation_code = code if code else get_invitation_code(purchase)
	result = _StorePurchaseInvitation(invitation_code, purchase)
	result.creator = purchase.creator
	return result
