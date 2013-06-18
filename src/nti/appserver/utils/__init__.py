# -*- coding: utf-8 -*-
"""
Appserver utils views

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson

class _JsonBodyView(object):

    def __init__(self, request):
        self.request = request

    def readInput(self):
        request = self.request
        if request.body:
            values = simplejson.loads(unicode(request.body, request.charset))
        else:
            values = {}
        return values

class CaseInsensitiveDict(dict):

    def __init__(self, **kwargs):
        super(CaseInsensitiveDict, self).__init__()
        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def has_key(self, key):
        return key.lower() in self.data

    def __setitem__(self, key, value):
        super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def get(self, key, default=None):
        return super(CaseInsensitiveDict, self).get(key.lower(), default)

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

    def __delitem__(self, key):
        return super(CaseInsensitiveDict, self).__delitem__(key.lower())
