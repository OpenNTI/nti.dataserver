#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementation of the :class:`nti.appserver.interfaces.IInvitations` utility.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import interface
from zope import component

from zope.container import contained

from zope.annotation import interfaces as an_interfaces
from zope.location import interfaces as loc_interfaces
from . import interfaces as invite_interfaces

import zc.intid as zc_intid

import persistent

from nti.dataserver import containers
from nti.externalization import integer_strings


@interface.implementer(invite_interfaces.IInvitations,
					   an_interfaces.IAttributeAnnotatable,
					   loc_interfaces.ISublocations)
class PersistentInvitations(persistent.Persistent,contained.Contained):
	"""
	Basic implementation of invitation storage.
	"""

	def __init__(self):
		self._invitations = containers.LastModifiedBTreeContainer()
		contained.contained( self._invitations, self, '_invitations' )

	def sublocations(self):
		yield self._invitations

		# If we have annotations, then if the annotated value thinks of
		# us as a parent, we need to return that. See zope.annotation.factory
		annotations = an_interfaces.IAnnotations(self, {})

		# Technically, IAnnotations doesn't have to be iterable of values,
		# but it always is (see zope.annotation.attribute)
		for val in annotations.values():
			if getattr( val, '__parent__', None ) is self: #pragma: no cover
				yield val

	def registerInvitation(self, invitation):
		if not invitation.code:
			iid = component.getUtility( zc_intid.IIntIds ).register( invitation )
			invitation.code = integer_strings.to_external_string( iid )

		# The container implementation raises KeyError if the key is already used
		self._invitations[invitation.code] = invitation

	def getInvitationByCode( self, code ):
		return self._invitations.get( code )

class ZcmlInvitations(PersistentInvitations):
	"""
	An invitations utility designed to be registered in ZCML configuration,
	and given only invitations that also come from ZCML configuration. This does
	not expect to be persisted, and does not use the IntId utility.
	"""

	def registerInvitation(self, invitation):
		if not invitation.code:
			raise KeyError('Invitation must already have a code.')

		super(ZcmlInvitations,self).registerInvitation( invitation )


def accept_invitations( user, invitation_codes ):
	"""
	Convenience method, typically used during an event listener for an event like
	:class:`nti.dataserver.users.interfaces.IWillCreateNewEntityEvent`. Makes the user
	accept all the invitations in the code list, raising errors if this cannot be done.
	"""
	utility = component.getUtility( invite_interfaces.IInvitations )
	for code in invitation_codes:
		invitation = utility.getInvitationByCode( code )
		if not invitation:
			raise invite_interfaces.InvitationCodeError( code )
		invitation.accept( user )
