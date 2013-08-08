# -*- coding: utf-8 -*-
"""
Search data structures

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import itertools

from brownie.caching import LFUCache

class LFUMap(LFUCache):

    def __init__(self, maxsize, on_removal_callback=None):
        super(LFUMap, self).__init__(maxsize=maxsize)
        self.on_removal_callback = on_removal_callback

    def __delitem__(self, key):
        if self.on_removal_callback:
            value = dict.__getitem__(self, key)
        super(LFUMap, self).__delitem__(key)
        if self.on_removal_callback:
            self.on_removal_callback(key, value)

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
