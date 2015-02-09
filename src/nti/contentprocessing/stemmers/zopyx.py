#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZOPYX based stemmers

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

try:
	from zopyx.txng3.ext import stemmer
except ImportError:
	stemmer = None

from .interfaces import IStemmer

lang_translation = {'en':'english', 'es':'spansih', 'ru':'russian',
					'fr':'french', 'de':'german', 'da':'danish',
					'nl':'dutch', 'it':'italian', 'no':'norwegian',
					'pt':'portuguese', 'sv':'swedish', 'fi':'finnish',
					'tr':'turkish', 'hu':'hungarian', 'ro':'romanian'}

@interface.implementer(IStemmer)
class _ZopyYXStemmer(object):

	__slots__ = ('stemmers')

	def __init__(self):
		self.stemmers = {}

	def _stemmer(self, lang='en'):
		lang = lang.lower() if lang else 'en'
		result = self.stemmers.get(lang, None)
		if result is None and stemmer is not None:
			language = lang_translation[lang]
			result = self.stemmers[lang] = stemmer.Stemmer(language)
		return result

	def stem(self, token, lang='en'):
		if stemmer is not None:
			token = unicode(token)
			result = self._stemmer(lang).stem((token,))
			return result[0] if result else token
		else:
			return token
