# -*- coding: utf-8 -*-
"""
NLTK based stemmers

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import nltk

from zope import interface

from . import interfaces as stemmer_interfaces

@interface.implementer(stemmer_interfaces.IStemmer)
class _PorterStemmer(object):

    __slots__ = ('stemmer',)

    def __init__(self):
        self.stemmer = nltk.PorterStemmer()

    def stem(self, token):
        token = unicode(token)
        result = self.stemmer.stem(token)
        return result if result else token
