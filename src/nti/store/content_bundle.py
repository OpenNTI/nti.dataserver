#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines content bundle object

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.annotation import interfaces as an_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IContentBundle,
					   an_interfaces.IAttributeAnnotatable)
class ContentBundle(SchemaConfigured):

	# create all interface fields
	createDirectFieldProperties(store_interfaces.IContentBundle)

	# Override Description to adapt to a content fragment
	Description = AdaptingFieldProperty(store_interfaces.IContentBundle['Description'])

	@property
	def id(self):
		return self.NTIID

	def __str__(self):
		return self.NTIID

	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__, self.NTIID, self.Items)

	def __eq__(self, other):
		try:
			return self is other or (store_interfaces.IContentBundle.providedBy(other)
									 and self.NTIID == other.NTIID)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.NTIID)
		return xhash


