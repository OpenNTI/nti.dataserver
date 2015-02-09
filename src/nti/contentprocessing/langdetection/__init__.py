#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.common.property import alias

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ILanguage

@WithRepr
@EqHash('code',)
@functools.total_ordering
@interface.implementer(ILanguage)
class Language(SchemaConfigured):
	createDirectFieldProperties(ILanguage)

	def __lt__(self, other):
		try:
			return self.code < other.code
		except AttributeError:
			return NotImplemented

	def __gt__(self, other):
		try:
			return self.code > other.code
		except AttributeError:
			return NotImplemented
