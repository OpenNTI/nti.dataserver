# -*- coding: utf-8 -*-
"""
Concept tagging objects

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from . import interfaces as cpct_interfaces

@interface.implementer(cpct_interfaces.IConceptSource)
class ConceptSource(object):

	def __init__(self, source, uri=None):
		self.uri = uri
		self.source = source

	def __eq__(self, other):
		try:
			return self is other or (self.source == other.source and self.uri == other.uri)
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
		return '%s(%s, %s)' % (self.__class__, self.source, self.uri)

@interface.implementer(cpct_interfaces.IConcept)
class Concept(object):

	def __init__(self, text, relevance, sources=()):
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
		return '%s(text=%s, relevance=%s, sources=%r)' % (self.__class__, self.text, self.relevance, self.sources)
