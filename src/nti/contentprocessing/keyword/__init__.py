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

from . import interfaces as cpkw_interfaces
	
@functools.total_ordering
@interface.implementer(cpkw_interfaces.IContentKeyWord)
class ContentKeyWord(object):

	__slots__ = ('token', 'relevance')

	def __init__(self, token=None, relevance=None):
		self.token = token
		self.relevance = relevance

	def __eq__(self, other):
		try:
			return self is other or self.token == other.token
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.token)
		return xhash

	def __str__(self):
		return self.token

	def __repr__(self):
		return '%s(%s,%s)' % (self.__class__.__name__, self.token, self.relevance)
	
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
	extractor = component.getUtility(cpkw_interfaces.ITermExtractKeyWordExtractor)
	result = extractor(content, lang=lang, filtername=filtername)
	return result

def extract_key_words(content):
	extractor = component.getUtility(cpkw_interfaces.IKeyWordExtractor)
	result = extractor(content)
	return result
