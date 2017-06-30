#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id:
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained

from zope.traversing.interfaces import IPathAdapter

from nti.appserver import SITE_ADMIN

from nti.appserver.workspaces.interfaces import ISiteAdminWorkspace

from nti.appserver.workspaces.interfaces import IUserService

from nti.dataserver.interfaces import IUser

from nti.property.property import alias


@interface.implementer(IPathAdapter)
@component.adapter(IUser, IRequest)
def SiteAdminWorkspacePathAdapter(context, request):
    service = IUserService(context)
    workspace = ISiteAdminWorkspace(service)
    return workspace


@interface.implementer(ISiteAdminWorkspace)
class _SiteAdminWorkspace(Contained):

    __name__ = SITE_ADMIN

    name = alias('__name__', __name__)

    def __init__(self, user_service):
        self.context = user_service
        self.user = user_service.user

    @Lazy
    def collections(self):
        pass

    @property
    def links(self):
        pass

    def __getitem__(self, key):
        pass

    def __len__(self):
        pass


@interface.implementer(ISiteAdminWorkspace)
@component.adapter(IUserService)
def SiteAdminWorkspace(user_service):
    workspace = _SiteAdminWorkspace(user_service)
    workspace.__parent__ = workspace.user
    return workspace
