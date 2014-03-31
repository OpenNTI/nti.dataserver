#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines content bundle object

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.annotation import interfaces as an_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as store_interfaces

from nti.externalization.externalization import make_repr

@interface.implementer(store_interfaces.IContentBundle,
					   an_interfaces.IAttributeAnnotatable)
class ContentBundle(SchemaConfigured):

	createDirectFieldProperties(store_interfaces.IContentBundle)
	Description = AdaptingFieldProperty(store_interfaces.IContentBundle['Description'])

	def __reduce__(self):
		# Not persistent!
		raise TypeError()

	@property
	def id(self):
		return self.NTIID

	def __str__(self):
		return self.NTIID

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return self is other or self.NTIID == other.NTIID
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.NTIID)
		return xhash
