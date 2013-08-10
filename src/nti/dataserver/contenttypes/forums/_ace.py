#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to ACE implementations for objects defined in this package.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.mimetype import interfaces as zmime_interfaces

from nti.dataserver import mimetype

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as frm_interfaces

@interface.implementer(frm_interfaces.IForumACE, zmime_interfaces.IContentTypeAware)
class ForumACE(SchemaConfigured):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	__external_class_name__ = "ACE"

	createDirectFieldProperties(frm_interfaces.IForumACE)

	def __str__(self):
		return "%s(%s,%s,%s)" % (self.__class__, self.Action, self.Permission, self.Entities)

	__repr__ = __str__

	def __eq__(self, other):
		try:
			return self is other or (self.Action == other.Action
									 and self.Permission == other.Permission
									 and set(self.Entities) == set(other.Entities))
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Action)
		xhash ^= hash(self.Entities)
		xhash ^= hash(self.Permission)
		return xhash
