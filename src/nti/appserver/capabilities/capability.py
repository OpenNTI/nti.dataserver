#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of capability objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.security import permission

from nti.appserver.capabilities.interfaces import ICapability

logger = __import__('logging').getLogger(__name__)


@interface.implementer(ICapability)
class Capability(permission.Permission):
    """
    Basic implementation of a :class:`.ICapability`.
    """

    def __init__(self, cap_id, title=u'', description=u''):
        super(Capability, self).__init__(cap_id, title=title, 
                                         description=description)
