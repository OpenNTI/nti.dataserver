#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from zope import interface

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from nti.dataserver.interfaces import ICommunityRoleManager

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICommunityRoleManager)
class PersistentCommunityRoleManager(AnnotationPrincipalRoleManager):
    """
    An implementation of :class:`ICommunityRoleManager` that will return
    persistently stored principals/roles.
    """
