#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directives to be used in ZCML: registering static invitations with known codes.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.configuration.fields import Tokens
from zope.configuration.fields import TextLine

from nti.invitations.interfaces import IInvitations
from nti.invitations.invitation import JoinCommunityInvitation

class IRegisterJoinCommunityInvitationDirective(interface.Interface):
	"""
	The arguments needed for registering an invitation to join communities.
	"""

	code = TextLine(
		title="The human readable/writable code the user types in. Should not have spaces.",
		required=True,
		)

	entities = Tokens(
		title="The global username or NTIIDs of communities or DFLs to join",
		required=True,
		value_type = TextLine(title="The entity identifier."),
		)

def _register(code, entities):
	invitations = component.getUtility(IInvitations)
	invitations.registerInvitation(JoinCommunityInvitation(code, entities))

def registerJoinCommunityInvitation(_context, code, entities):
	"""
	Register an invitation with the given code that, at runtime,
	will resolve and try to join the named entities.

	:param module module: The module to inspect.
	"""
	_context.action(discriminator=('registerJoinCommunityInvitation', code),
					callable=_register,
					args=(code, entities))
