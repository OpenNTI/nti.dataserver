#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines an ldap registration object

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.annotation import interfaces as an_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as util_interfaces

@interface.implementer(util_interfaces.ILDAP, an_interfaces.IAttributeAnnotatable)
class LDAP(SchemaConfigured):
	createDirectFieldProperties(util_interfaces.ILDAP)

	@property
	def id(self):
		return self.ID

	def __str__(self):
		return self.URL

	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__, self.URL, self.Usermame)

	def __eq__(self, other):
		try:
			return self is other or (util_interfaces.ILDAP.providedBy(other)
									 and self.ID == other.ID)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.ID)
		return xhash
