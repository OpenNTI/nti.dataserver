# -*- coding: utf-8 -*-
"""
Store invitations

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zc.intid as zc_intid

from zope import component

from nti.appserver.invitations.invitation import JoinEntitiesInvitation

from nti.externalization import integer_strings

from nti.zodb import minmax

from .purchase_history import get_purchase_attempt
from ._content_roles import _add_users_content_roles

class InviationCapcityExceeded(Exception):
	"""
	Raised when a user is attempting to accept an invitation whose capacity has been exceeded.
	"""

	i18n_message = _("The limit for this invitation code has been exceeded.")
	
class _StoreEntityInvitation(JoinEntitiesInvitation):
	
	def __init__( self, purchase_id, username, code, entities, capacity=None ):
		super(_StoreEntityInvitation, self).__init__(code, entities)
		self.creator = username
		self.purchase_id = purchase_id
		self.capacity = capacity
		self._tokens = minmax.NumericMinimum( self.capacity ) if capacity else None

	def consume(self):
		if self._tokens:
			if self._tokens.value > 0:
				self._tokens -= 1
			else:
				return False
		return True

	def accept( self, user ):
		if self.consume():
			super(_StoreEntityInvitation,self).accept( user )
			purchase = get_purchase_attempt(self.purchase_id, self.creator)
			_add_users_content_roles(user, purchase.Items)
		else:
			raise InviationCapcityExceeded()
		
def create_store_inviation(purchase_id, username, entities, capacity=None):
	purchase = get_purchase_attempt(purchase_id, username)
	iid = component.getUtility( zc_intid.IIntIds ).getId( purchase )
	invitation_code = integer_strings.to_external_string( iid )
	return _StoreEntityInvitation(purchase_id, username, invitation_code, entities, capacity)
