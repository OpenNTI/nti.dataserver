#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Relating to ACE implementations for objects defined in this package.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.mimetype import interfaces as zmime_interfaces

from nti.dataserver import interfaces as nti_interfacess

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from . import interfaces as frm_interfaces

@interface.implementer(frm_interfaces.IForumACE,
					   nti_interfacess.IACE,
					   zmime_interfaces.IContentTypeAware)
class ForumACE(SchemaConfigured):
	mimeType = mime_type = u'application/vnd.nextthought.forums.ace'
	createDirectFieldProperties(frm_interfaces.IForumACE)

	def __iter__(self):
		for perm in self.Permissions:
			for entity in self.Entities:
				yield (self.Action, entity, perm)

	def __str__(self):
		return "%s(%s,%s,%s)" % (self.__class__.__name__, self.Action,
								 self.Permissions, self.Entities)
	__repr__ = __str__

	def __eq__(self, other):
		try:
			return self is other or (self.Action == other.Action
									 and set(self.Entities) == set(other.Entities)
									 and set(self.Permissions) == set(other.Permissions))
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Action)
		xhash ^= hash(self.Entities)
		xhash ^= hash(self.Permissions)
		return xhash
