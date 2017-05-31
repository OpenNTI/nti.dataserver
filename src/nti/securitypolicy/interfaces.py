#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.securitypolicy.interfaces import IPrincipalRoleManager


class ISiteRoleManager(IPrincipalRoleManager):
    """
    An IPrincipalRoleManager that can be used to grant
    roles to principals on a site by site basis.  To grant
    a role to a principal in a specific site, register an
    instance of SIteRoleManager as a utility in a registerIn block
    for this interface.  With the utilty registered, the
    siteGrant zcml directive can be used to assign
    roles to a principals within the context of that site.
    """
