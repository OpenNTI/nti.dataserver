#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Grade book

$Id: graders.py 19693 2013-05-30 23:06:02Z carlos.sanchez $
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces
from zope.mimetype import interfaces as zmime_interfaces

from persistent import Persistent

from nti.dataserver import mimetype
from nti.dataserver import containers as nti_containers
from nti.dataserver.datastructures import CreatedModDateTrackingObject

from nti.utils.schema import AdaptingFieldProperty

from . import interfaces as book_interfaces

@interface.implementer(book_interfaces.IGradeBook, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class GradeBook(nti_containers.CheckingLastModifiedBTreeContainer, zcontained.Contained):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

@interface.implementer(book_interfaces.IGradeBookPart, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class GradeBookPart(nti_containers.CheckingLastModifiedBTreeContainer, zcontained.Contained):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	name = AdaptingFieldProperty(book_interfaces.IGradeBookEntry['name'])
	order = AdaptingFieldProperty(book_interfaces.IGradeBookEntry['order'])
	weight = AdaptingFieldProperty(book_interfaces.IGradeBookEntry['weight'])

	def __str__(self):
		return self.name

	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__.__name__, self.name, self.weight)


@interface.implementer(book_interfaces.IGradeBookEntry, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class GradeBookEntry(Persistent, CreatedModDateTrackingObject, zcontained.Contained):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	name = AdaptingFieldProperty(book_interfaces.IGradeBookEntry['name'])
	order = AdaptingFieldProperty(book_interfaces.IGradeBookEntry['order'])
	NTIID = AdaptingFieldProperty(book_interfaces.IGradeBookEntry['NTIID'])
	weight = AdaptingFieldProperty(book_interfaces.IGradeBookEntry['weight'])
	questionSetID = AdaptingFieldProperty(book_interfaces.IGradeBookEntry['questionSetID'])

	def __str__(self):
		return self.name

	def __repr__(self):
		return "%s(%s,%s,%s)" % (self.__class__.__name__, self.name, self.weight, self.NTIID)

	def __eq__(self, other):
		try:
			return self is other or (book_interfaces.IGradeBookEntry.providedBy(other)
									 and self.NTIID == other.NTIID)
		except AttributeError:
			return NotImplemented

