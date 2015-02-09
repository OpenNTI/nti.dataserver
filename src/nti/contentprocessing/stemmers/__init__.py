#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stemmer module

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import repoze.lru

from zope import component
from zope import interface

from .interfaces import IStemmer

@repoze.lru.lru_cache(1000)
def stem_word(word, lang='en', name=''):
    stemmer = component.getUtility(IStemmer, name=name)
    result = stemmer.stem(unicode(word), lang) if word else None
    return result
