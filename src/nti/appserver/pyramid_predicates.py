#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class ContentTypePredicate(object):

    def __init__(self, val, unused_config):
        self.val = val

    def text(self):
        return u'content type = %s' % self.val
    phash = text

    def __call__(self, unused_context, request):
        return request.content_type == self.val
