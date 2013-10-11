#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Grade book

$Id$
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

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as book_interfaces

@interface.implementer(book_interfaces.IGrade, zmime_interfaces.IContentTypeAware)
class Grade(Persistent, SchemaConfigured, zcontained.Contained):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	createDirectFieldProperties(book_interfaces.IGrade)

	def __str__(self):
		return self.grade

	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__.__name__, self.grade, self.autograde)

@interface.implementer(book_interfaces.IUserGrades, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class UserGrades(nti_containers.CheckingLastModifiedBTreeContainer, zcontained.Contained):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass


@interface.implementer(book_interfaces.IGradeBookEntry, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class Grades(nti_containers.CheckingLastModifiedBTreeContainer, zcontained.Contained):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
