#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from . import interfaces as util_interfaces

@interface.implementer(util_interfaces.IOAuthKeys)
class OAuthKeys(SchemaConfigured):
	createDirectFieldProperties(util_interfaces.IOAuthKeys)

	@property
	def id(self):
		return self.APIKey

	def __str__(self):
		return self.APIKey

	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__.__name__, self.APIKey, self.SecretKey)

	def __eq__(self, other):
		try:
			return self is other or (self.APIKey == other.APIKey and
									 self.SecretKey == other.SecretKey)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.APIKey)
		xhash ^= hash(self.SecretKey)
		return xhash

