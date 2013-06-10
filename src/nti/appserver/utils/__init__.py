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
