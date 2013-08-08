#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with maps.

$Id: sets.py 9464 2012-07-29 19:25:37Z jason.madden $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

class CaseInsensitiveDict(dict):

    def __init__(self, **kwargs):
        super(CaseInsensitiveDict, self).__init__()
        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def has_key(self, key):
        return super(CaseInsensitiveDict, self).has_key(key.lower())

    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def get(self, key, default=None):
        return super(CaseInsensitiveDict, self).get(key.lower(), default)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

    def __delitem__(self, key):
        return super(CaseInsensitiveDict, self).__delitem__(key.lower())
