#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from zope.container.traversal import ContainerTraversable

from zope.traversing.interfaces import ITraversable

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

    # pylint: disable=arguments-differ
    def traverse(self, key, remaining_path):
        if key == UNAUTHENTICATED_PRINCIPAL_NAME:
            return AnonymousUser(self.context)
        return ContainerTraversable.traverse(self, key, remaining_path)
