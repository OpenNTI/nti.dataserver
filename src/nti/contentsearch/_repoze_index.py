#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.deprecation import deprecated

deprecated('get_sharedWith', 'No longer used. BWC only')
def get_sharedWith(*args, **kwargs):
    return ()

deprecated('get_object_ngrams', 'No longer used. BWC only')
def get_object_ngrams(*args, **kwargs):
    return ()

deprecated('get_object_content', 'No longer used. BWC only')
def get_object_content(*args, **kwargs):
    return None
