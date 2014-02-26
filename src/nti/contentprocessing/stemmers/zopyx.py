#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZOPYX based stemmers

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zopyx.txng3.ext import stemmer

from . import interfaces as stemmer_interfaces

@interface.implementer(stemmer_interfaces.IStemmer)
class ZopyYXStemmer(object):

    __slots__ = ('stemmer',)

    def __init__(self, language='english'):
        self.stemmer = stemmer.Stemmer(language)

    def stem(self, token):
        token = unicode(token)
        result = self.stemmer.stem((token,))
        return result[0] if result else token
