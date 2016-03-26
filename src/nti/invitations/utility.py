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

from zope.annotation.interfaces import IAnnotations
from zope.annotation.interfaces import IAttributeAnnotatable

from zope.container.contained import contained
from zope.container.contained import Contained

from zope.intid.interfaces import IIntIds

from zope.location.interfaces import ISublocations

from persistent import Persistent

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.externalization import integer_strings

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitations
from nti.invitations.interfaces import InvitationCodeError

def get_invitation_code(invitation):
	iid = component.getUtility(IIntIds).register(invitation)
	result = integer_strings.to_external_string(iid)
	return result

@interface.implementer(IInvitations,
					   IAttributeAnnotatable,
					   ISublocations)
class PersistentInvitations(Persistent, Contained):
	"""
	Basic implementation of invitation storage.
	"""

	def __init__(self):
		self._invitations = CheckingLastModifiedBTreeContainer()
		contained(self._invitations, self, '_invitations')

	def sublocations(self):
		yield self._invitations

		# If we have annotations, then if the annotated value thinks of
		# us as a parent, we need to return that. See zope.annotation.factory
		annotations = IAnnotations(self, {})

		# Technically, IAnnotations doesn't have to be iterable of values,
		# but it always is (see zope.annotation.attribute)
		for val in annotations.values():
			if getattr(val, '__parent__', None) is self:  # pragma: no cover
				yield val

	def registerInvitation(self, invitation):
		if not invitation.code:
			code = get_invitation_code(invitation)
			invitation.code = code
		# The container implementation raises KeyError if the key is already used
		self._invitations[invitation.code] = invitation

	def removeInvitation(self, invitation):
		if IInvitation.providedBy(invitation):
			if not invitation.code:
				raise KeyError('Invitation must already have a code.')
			invitation = invitation.code
		del self._invitations[invitation]

	def getInvitationByCode(self, code):
		code = code.strip() if code else code
		return self._invitations.get(code)

class ZcmlInvitations(PersistentInvitations):
	"""
	An invitations utility designed to be registered in ZCML configuration,
	and given only invitations that also come from ZCML configuration. This does
	not expect to be persisted, and does not use the IntId utility.
	"""

	def registerInvitation(self, invitation):
		if not invitation.code:
			raise KeyError('Invitation must already have a code.')
		super(ZcmlInvitations, self).registerInvitation(invitation)

def accept_invitations(user, invitation_codes):
	"""
	Convenience method, typically used during an event listener for an event like
	:class:`nti.dataserver.users.interfaces.IWillCreateNewEntityEvent`. Makes the user
	accept all the invitations in the code list, raising errors if this cannot be done.
	"""
	result = {}
	utility = component.getUtility(IInvitations)
	for code in invitation_codes:
		invitation = utility.getInvitationByCode(code)
		if not invitation:
			raise InvitationCodeError(code)
		if invitation.accept(user):
			result[code] = invitation
	return result
