# -*- coding: utf-8 -*-
"""
Implementations of API alchemy keys.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import interfaces

@interface.implementer(interfaces.IAlchemyAPIKey)
class AlchemyAPIKey(object):

	__slots__ = ('name', 'value')

	def __init__(self, name, value):
		self.name = name
		self.value = value

	@property
	def alias(self):
		return self.name

	@property
	def key(self):
		return self.value

	def __eq__(self, other):
		try:
			return self is other or (self.name == other.name
									 and self.value == other.value)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.name)
		xhash ^= hash(self.value)
		return xhash

	def __repr__(self):
		return "%s(%s, %s)" % (self.__class__.__name__, self.name, self.value)

	__str__ = __repr__

def create_api_key(name, value):
	result = AlchemyAPIKey(name=name, value=value)
	return result
