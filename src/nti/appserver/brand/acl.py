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

from nti.appserver.brand.interfaces import ISiteBrand

from nti.dataserver.authorization import ROLE_ADMIN

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.authorization_acl import acl_from_aces

from nti.dataserver.interfaces import ALL_PERMISSIONS

from nti.dataserver.interfaces import IACLProvider

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IACLProvider)
@component.adapter(ISiteBrand)
class SiteBrandACLProvider(object):

    def __init__(self, context):
        self.context = context

    @property
    def __parent__(self):
        return self.context.__parent__

    @property
    def __acl__(self):
        acl = [ace_allowing(ROLE_ADMIN, ALL_PERMISSIONS, type(self))]
        result = acl_from_aces(acl)
        return result
