#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NLTK based stemmers

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

try:
	from nltk import PorterStemmer
except ImportError:
	class PorterStemmer(object):
		def stem(self, x): return x
	
from .interfaces import IStemmer

@interface.implementer(IStemmer)
class _PorterStemmer(object):

	def __init__(self, *args, **kwargs):
		pass

	def stem(self, token, lang='en'):
		token = unicode(token)
		# The underlying stemmer object is NOT thread safe,
		# it must not be used concurrently
		stemmer = PorterStemmer()
		result = stemmer.stem(token)
		return result if result else token
