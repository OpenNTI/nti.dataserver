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

from nti.dataserver import mimetype
from nti.dataserver.datastructures import ModDateTrackingObject

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from nti.zodb.persistentproperty import PersistentPropertyHolder

from . import interfaces as book_interfaces

@interface.implementer(book_interfaces.IGradeBook, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class GradeBook(ModDateTrackingObject, SchemaConfigured, zcontained.Contained, PersistentPropertyHolder):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(book_interfaces.IGradeBook)


@interface.implementer(book_interfaces.IGradeBookPart, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class GradeBookPart(SchemaConfigured, zcontained.Contained):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(book_interfaces.IGradeBookPart)


@interface.implementer(book_interfaces.IGradeBookEntry, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class GradeBookEntry(SchemaConfigured, zcontained.Contained):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(book_interfaces.IGradeBookEntry)
