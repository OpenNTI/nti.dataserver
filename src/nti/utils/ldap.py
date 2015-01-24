#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines an ldap registration object

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.schema.schema import EqHash
from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .property import alias

from .interfaces import ILDAP

from .cypher import get_plaintext

@interface.implementer(ILDAP)
@EqHash('ID')
class LDAP(SchemaConfigured):
	createDirectFieldProperties(ILDAP)

	password = alias('Password')
	
	@property
	def id(self):
		return self.ID

	def __str__(self):
		return self.URL

	def __setattr__(self, name, value):
		if name in ("Password", "password"):
			try:
				key = get_plaintext(value)
				value = unicode(key)
			except (TypeError, StandardError):
				pass
		return SchemaConfigured.__setattr__(self, name, value)
