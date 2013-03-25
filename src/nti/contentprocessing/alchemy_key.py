# -*- coding: utf-8 -*-
"""
Implementations of API alchemy keys.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from . import interfaces

@interface.implementer(interfaces.IAlchemyAPIKey)
class AlchemyAPIKey(object):

	__slots__ = ('alias', 'value')

	def __init__(self, alias, value):
		self.alias = alias
		self.value = value

	@property
	def name(self):
		return self.alias

	@property
	def key(self):
		return self.value

	def __eq__(self, other):
		try:
			return self is other or (self.alias == other.alias and self.value == other.value)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.alias)
		xhash ^= hash(self.value)
		return xhash

	def __repr__(self):
		return "AlchemyAPIKey(%s, %s)" % (self.alias, self.value)

	__str__ = __repr__
