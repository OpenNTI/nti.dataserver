#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.security.interfaces import IPrincipal

from nti.contentfolder.interfaces import ILockedFolder
from nti.contentfolder.interfaces import IContentFolder

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_UPDATE
from nti.dataserver.authorization import ROLE_ADMIN
from nti.dataserver.authorization import ROLE_CONTENT_ADMIN

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import ALL_PERMISSIONS


@component.adapter(IContentFolder)
@interface.implementer(IACLProvider)
class ContentFolderACLProvider(object):
    """
    Provides the basic ACL for a content folder.
    """

    def __init__(self, context):
        self.context = context

    @property
    def __parent__(self):
        # See comments in nti.dataserver.authorization_acl:has_permission
        return self.context.__parent__

    @Lazy
    def __aces__(self):
        aces = [ace_allowing(ROLE_ADMIN, ALL_PERMISSIONS, type(self))]
        if ILockedFolder.providedBy(self.context):
            for perm in (ACT_READ, ACT_UPDATE):
                aces.append(ace_allowing(ROLE_CONTENT_ADMIN, perm, type(self)))
        else:
            ace = ace_allowing(ROLE_CONTENT_ADMIN, ALL_PERMISSIONS, type(self))
            aces.append(ace)
        creator = IPrincipal(self.context.creator, None)
        if creator is not None:
            if ILockedFolder.providedBy(self.context):
                aces.append(ace_allowing(creator, ACT_READ, type(self)))
                aces.append(ace_allowing(creator, ACT_UPDATE, type(self)))
            else:
                aces.append(ace_allowing(creator, ALL_PERMISSIONS, type(self)))
        return aces

    @Lazy
    def __acl__(self):
        return acl_from_aces(self.__aces__)
