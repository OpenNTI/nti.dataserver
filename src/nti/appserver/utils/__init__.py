#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

import simplejson
import collections

from nti.common.maps import CaseInsensitiveDict

class _JsonBodyView(object):

    def __init__(self, request):
        self.request = request

    def readInput(self):
        request = self.request
        if request.body:
            values = simplejson.loads(unicode(request.body, request.charset))
            values = CaseInsensitiveDict(**values) \
            if isinstance(values, collections.Mapping) else values
        else:
            values = {}
        return values
