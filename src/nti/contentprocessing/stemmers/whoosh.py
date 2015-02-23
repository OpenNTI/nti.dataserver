#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh based stemmers

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

try:
    from whoosh.lang import stemmer_for_language
except ImportError:
    stemmer_for_language = lambda x: x
    
from .interfaces import IStemmer

@interface.implementer(IStemmer)
class _WhooshStemmer(object):

    def __init__(self, *args, **kwargs):
        pass

    def stem(self, token, language='en'):
        stemmer = stemmer_for_language(language)
        token = unicode(token)
        result = stemmer(token)
        return result if result else token
