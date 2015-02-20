#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for using NTIIDs in a zope schema.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.schema.field import ValidURI

from .ntiids import validate_ntiid_string

class ValidNTIID(ValidURI):
	"""
	A schema field that checks that the value is a correctly
	formed NTIID. (This does not perform any validation that the
	value is actually reachable or accessibly in a library or
	catalog.)
	"""
	_type = unicode

	def fromUnicode(self, value):
		# The very first thing the superclass does is turn
		# the value into a bytestring again (under py2),
		# which is obviously wrong for us. So skip that.
		value = value.strip()
		self.validate(value)
		return value

	def _validate(self, value):
		super(ValidNTIID,self)._validate(value)
		validate_ntiid_string( value )
