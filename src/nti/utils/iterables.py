#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with iterables/sequences.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import itertools

class IterableWrapper(object):

    def __init__(self, it, size=0):
        self.it = it
        self.size = size

    def __len__(self):
        return self.size

    def __iter__(self):
        for elt in self.it:
            yield elt

    def __getitem__(self, index):
        if type(index) is slice:
            return list(itertools.islice(self.it, index.start, index.stop, index.step))
        else:
            return next(itertools.islice(self.it, index, index + 1))

