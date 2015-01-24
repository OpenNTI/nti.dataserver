#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
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

from .cypher import get_plaintext

from .interfaces import IOAuthKeys

@interface.implementer(IOAuthKeys)
@EqHash('APIKey', 'SecretKey')
class OAuthKeys(SchemaConfigured):
	createDirectFieldProperties(IOAuthKeys)
	
	apiKey = alias('APIKey')
	secretKey = alias('SecretKey')
	
	@property
	def id(self):
		return self.APIKey

	def __str__(self):
		return self.APIKey

	def __setattr__(self, name, value):
		if name in ("apiKey", "APIKey", "secretKey", "SecretKey"):
			try:
				key = get_plaintext(value)
				value = unicode(key)
			except (TypeError, StandardError):
				pass
		return SchemaConfigured.__setattr__(self, name, value)
