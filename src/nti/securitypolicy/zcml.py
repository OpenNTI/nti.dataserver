#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZCML directives to grant roles and permissions. Just like
those provided by :mod:`zcml.securitypolicy`, but not restricted
to Python identifiers for names (e.g., allows email-style names).

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import component

from zope.interface import Interface

from zope.principalregistry.metadirectives import IDefinePrincipalDirective as _IDefinePrincipalDirective

from zope.security.zcml import Permission
from zope.security.zcml import IPermissionDirective

from zope.schema import TextLine

from nti.securitypolicy.interfaces import ISiteRoleManager

logger = __import__('logging').getLogger(__name__)


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
    Grant roles to principals for an ISite
    """


class IDefineRoleDirective(IPermissionDirective):
    """
    Define a new role.
    """

    id = TextLine(
        title=u"Id",
        description=u"Id as which this object will be known and used.",
        required=True)


class IDefinePrincipalDirective(_IDefinePrincipalDirective):

    id = TextLine(
        title=u"Id",
        description=u"Id as which this object will be known and used.",
        required=True)

    password = TextLine(
        title=u"Password",
        description=u"Specifies the Principal's Password.",
        default=u'',
        required=True)

    password_manager = TextLine(
        title=u"Password Manager Name",
        description=u"Name of the password manager will be used "
        u"for encode/check the password",
        default=u"This Manager Does Not Exist",
        required=False)


def text_(s, encoding='utf-8', err='strict'):
    if isinstance(s, bytes):
        s = s.decode(encoding, err)
    return s


def _perform_site_role_grant(role, principal):
    role_manager = component.getUtility(ISiteRoleManager)
    role_manager.assignRoleToPrincipal(role, principal, check=False)


def grant_site(_context, principal=None, role=None):
    if principal and role:
        role = text_(role)
        principal = text_(principal)
        _context.action(
            discriminator=('grantRoleToPrincipal', role, principal),
            callable=_perform_site_role_grant,
            args=(role, principal),
        )
