#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import interfaces as app_interfaces

@interface.implementer(app_interfaces.ICommonIndexMap)
class CommonIndexMap(dict):

    def __init__(self):
        super(CommonIndexMap, self).__init__()
        self.by_container = {}

    def clear(self):
        super(CommonIndexMap, self).clear()
        self.by_container.clear()
