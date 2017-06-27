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

from zope.container.traversal import ContainerTraversable

from zope.traversing.interfaces import ITraversable

from pyramid.interfaces import IRequest

from nti.dataserver.interfaces import IUser


@interface.implementer(ITraversable)
@component.adapter(IUser, IRequest)
class UserAdapterTraversable(ContainerTraversable):
    pass
