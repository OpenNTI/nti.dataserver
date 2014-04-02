#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.property import alias
from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as ld_interfaces

@interface.implementer(ld_interfaces.ILanguage)
class Language(SchemaConfigured):
	createDirectFieldProperties(ld_interfaces.ILanguage)

	def __str__(self):
		return self.code

	def __repr__(self):
		return "%s(%s)" % (self.__class__.__name__, self.code)

	def __eq__(self, other):
		try:
			return self is other or self.code == other.code
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.code)
		return xhash
