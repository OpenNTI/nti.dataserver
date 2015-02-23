#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import codecs

from zope import interface

from nti.common.property import Lazy

from ..interfaces import IStopWords

@interface.implementer(IStopWords)
class FileBasedStopWords(object):

	@Lazy
	def _cache(self):
		result = {}
		path = os.path.join(os.path.dirname(__file__), 'data')
		for name in os.listdir(path):
			if not name.endswith('.txt'):
				continue
			lang = name[:-4]
			name = os.path.join(path, name)
			with codecs.open(name, "r", "utf-8") as fp:
				lines = {x.strip().lower() for x in fp.readlines()
						 if x and not x.startswith('#')}
				result[lang] = tuple(sorted(lines))
		return result

	def stopwords(self, lang='en'):
		return self._cache.get(lang, ())

	def available_languages(self):
		return tuple(sorted(self._cache.keys()))
_FileBasedStopWords = FileBasedStopWords

@interface.implementer(IStopWords)
class NoStopWords(object):

	__slots__ = ()

	def stopwords(self, lang='en'):
		return ()

	def available_languages(self,):
		return ('en', 'es', 'ru')

_DefaultStopWords = _NoStopWords = NoStopWords
