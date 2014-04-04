#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Concept tagging objects

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface

from . import interfaces as ct_interfaces

@interface.implementer(ct_interfaces.IConceptSource)
class ConceptSource(object):

	__slots__ = ('uri', 'source')

	def __init__(self, source, uri=None):
		self.uri = uri
		self.source = source

	def __eq__(self, other):
		try:
			return self is other or (self.source == other.source
									 and self.uri == other.uri)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.uri)
		xhash ^= hash(self.source)
		return xhash

	def __str__(self):
		return self.source

	def __repr__(self):
		return '%s(%s, %s)' % (self.__class__.__name__, self.source, self.uri)

@functools.total_ordering
@interface.implementer(ct_interfaces.IConcept)
class Concept(object):

	__slots__ = ('text', 'relevance', 'sources')

	def __init__(self, text=None, relevance=None, sources=()):
		self.text = text
		self.sources = sources
		self.relevance = relevance

	@property
	def sourcemap(self):
		result = {c.source:c.uri for c in self.sources}
		return result

	def __str__(self):
		return self.text

	def __repr__(self):
		return '%s(text=%s, relevance=%s, sources=%r)' % (self.__class__.__name__,
														  self.text,
														  self.relevance,
														  self.sources)

	def __eq__(self, other):
		try:
			return self is other or self.text == other.text
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.text)
		return xhash

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
