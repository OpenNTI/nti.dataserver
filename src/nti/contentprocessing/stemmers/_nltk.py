#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

import nltk

from nti.contentprocessing.stemmers import interfaces as stemmer_interfaces

@interface.implementer(stemmer_interfaces.IStemmer)
class _PorterStemmer(object):
    def __init__(self):
        self.stemmer = nltk.PorterStemmer()

    def stem(self, token):
        token = unicode(token)
        result = self.stemmer.stem(token)
        return result if result else token
