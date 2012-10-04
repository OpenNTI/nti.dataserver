#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML: registering static invitations with known codes.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


import zope.configuration.fields
from zope import interface
from zope import component


from . import interfaces as invite_interfaces
from . import invitation

class IRegisterJoinCommunityInvitationDirective(interface.Interface):
	"""
	The arguments needed for registering an invitation to join communities.
	"""

	code = zope.configuration.fields.TextLine(
		title="The human readable/writable code the user types in. Should not have spaces.",
		required=True,
		)

	entities = zope.configuration.fields.Tokens(
		title="The global username or NTIIDs of communities or DFLs to join",
		required=True,
		value_type = zope.configuration.fields.TextLine(title="The entity identifier."),
		)

def _register( code, entities ):
	invitations = component.getUtility( invite_interfaces.IInvitations )
	invitations.registerInvitation( invitation.JoinCommunityInvitation( code, entities ) )

def registerJoinCommunityInvitation( _context, code, entities ):
	"""
	Register an invitation with the given code that, at runtime,
	will resolve and try to join the named entities.

	:param module module: The module to inspect.
	"""
	_context.action(
		discriminator=('registerJoinCommunityInvitation', code ),
		callable=_register,
		args=(code,entities) )
