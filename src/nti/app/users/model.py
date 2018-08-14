#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from BTrees.OLBTree import OLBTree

from zope import interface

from zope.container.contained import Contained

from nti.coremetadata.interfaces import IContextLastSeenContainer

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IContextLastSeenContainer)
class ContextLastSeenContainer(OLBTree, Contained):

    def __init__(self):
        OLBTree.__init__(self)

    def append(self, item, timestamp=None):
        timestamp = timestamp or time.time()
        ntiid = getattr(item, 'ntiid', item)
        self[ntiid] = int(timestamp)

    def extend(self, items, timestamp=None):
        timestamp = timestamp or time.time()
        for item in items or ():
            self.append(item, timestamp)

    def contexts(self):
        return list(self.keys())
