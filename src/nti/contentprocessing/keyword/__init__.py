#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Keyword extractor module

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools
from collections import namedtuple

from zope import component
from zope import interface

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash

from .interfaces import IContentKeyWord
from .interfaces import IKeyWordExtractor
from .interfaces import ITermExtractKeyWordExtractor

@WithRepr
@EqHash('token',)
@functools.total_ordering
@interface.implementer(IContentKeyWord)
class ContentKeyWord(object):

	__slots__ = ('token', 'relevance')

	def __init__(self, token=None, relevance=None):
		self.token = token
		self.relevance = relevance

	def __lt__(self, other):
		try:
			return self.relevance < other.relevance
		except AttributeError:
			return NotImplemented

	def __gt__(self, other):
		try:
			return self.relevance > other.relevance
		except AttributeError:
			return NotImplemented

def term_extract_key_words(content, lang='en', filtername=u''):
	extractor = component.getUtility(ITermExtractKeyWordExtractor)
	result = extractor(content, lang=lang, filtername=filtername)
	return result

def extract_key_words(content):
	extractor = component.getUtility(IKeyWordExtractor)
	result = extractor(content)
	return result
