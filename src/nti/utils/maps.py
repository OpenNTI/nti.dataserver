#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with maps.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import collections

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

class CaseInsensitiveDict(dict):

    def __init__(self, *args, **kwargs):
        super(CaseInsensitiveDict, self).__init__()
        self.update(**kwargs)
        for arg in args or ():
            self.update(arg)

    def has_key(self, key):
        return super(CaseInsensitiveDict, self).has_key(key.lower())

    def __contains__(self, key):
        return super(CaseInsensitiveDict, self).__contains__(key.lower())

    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def get(self, key, default=None):
        return super(CaseInsensitiveDict, self).get(key.lower(), default)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

    def __delitem__(self, key):
        return super(CaseInsensitiveDict, self).__delitem__(key.lower())

    def update(self, *args, **kwargs):

        other = args[0] if len(args) >= 1 else ()

        if isinstance(other, collections.Mapping):
            for key in other:
                self.__setitem__(str(key), other[key])
        elif hasattr(other, "keys"):
            for key in other.keys():
                self.__setitem__(str(key), other[key])
        else:
            for key, value in other:
                self.__setitem__(str(key), value)

        for key, value in kwargs.items():
            self.__setitem__(str(key), value)

