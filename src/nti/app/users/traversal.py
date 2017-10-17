#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.container.traversal import ContainerTraversable

from zope.traversing.interfaces import ITraversable

from pyramid import httpexceptions as hexc

from pyramid.interfaces import IRequest

from nti.dataserver.interfaces import UNAUTHENTICATED_PRINCIPAL_NAME

from nti.dataserver.interfaces import IUsersFolder
from nti.dataserver.interfaces import AnonymousUser

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ITraversable)
@component.adapter(IUsersFolder, IRequest)
class UsersAdapterTraversable(ContainerTraversable):

    def __init__(self, context, request=None):
        ContainerTraversable.__init__(self, context)
        self.context = context
        self.request = request

    @property
    def authenticated_userid(self):
        try:
            return self.request.authenticated_userid
        except AttributeError:
            return None

    def traverse(self, key, remaining_path):
        if not bool(self.authenticated_userid):
            if key == UNAUTHENTICATED_PRINCIPAL_NAME:
                return AnonymousUser(self.context)
            raise hexc.HTTPForbidden()
        return ContainerTraversable.traverse(self, key, remaining_path)
