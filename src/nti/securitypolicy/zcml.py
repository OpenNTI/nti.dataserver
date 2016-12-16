#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives to grant roles and permissions. Just like
those provided by :mod:`zcml.securitypolicy`, but not restricted
to Python identifiers for names (e.g., allows email-style names).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.interface import Interface

from zope.principalregistry.metadirectives import IDefinePrincipalDirective as _IDefinePrincipalDirective

from zope.security.zcml import Permission
from zope.security.zcml import IPermissionDirective

from zope.schema import TextLine

from nti.dataserver.interfaces import ISiteRoleManager

class IGrantAllDirective(Interface):
	"""
	Grant Permissions to roles and principals and roles to principals.
	"""

	principal = TextLine(
		title=u"Principal",
		description=u"Specifies the Principal to be mapped.",
		required=False)

	role = TextLine(
		title=u"Role",
		description=u"Specifies the Role to be mapped.",
		required=False)

class IGrantDirective(IGrantAllDirective):
	"""
	Grant Permissions to roles and principals and roles to principals.
	"""

	permission = Permission(
		title=u"Permission",
		description=u"Specifies the Permission to be mapped.",
		required=False)

class IGrantSiteDirective(IGrantAllDirective):
	"""
	Grant roles to prinipals for an ISite
	"""

class IDefineRoleDirective(IPermissionDirective):
	"""
	Define a new role.
	"""

	id = TextLine(
		title="Id",
		description="Id as which this object will be known and used.",
		required=True)

class IDefinePrincipalDirective(_IDefinePrincipalDirective):

	id = TextLine(
		title="Id",
		description="Id as which this object will be known and used.",
		required=True)

	password = TextLine(
		title="Password",
		description="Specifies the Principal's Password.",
		default='',
		required=True)

	password_manager = TextLine(
		title="Password Manager Name",
		description="Name of the password manager will be used"
			" for encode/check the password",
		default="This Manager Does Not Exist",
		required=False)

def _perform_site_role_grant(role, principal):
	role_manager = component.queryUtility(ISiteRoleManager)
	if role_manager is not None:
		role_manager.assignRoleToPrincipal(role, principal, check=False)

def grant_site(_context, principal=None, role=None):
	if principal and role:
		_context.action(
            discriminator=('grantRoleToPrincipal', role, principal),
            callable=_perform_site_role_grant,
            args=(role, principal),
        )
