#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Grades

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.annotation import interfaces as an_interfaces
from zope.mimetype import interfaces as zmime_interfaces

from zc.blist import BList

from persistent.mapping import PersistentMapping

from nti.dataserver import mimetype
from nti.dataserver.datastructures import CreatedModDateTrackingObject

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as grades_interfaces

@interface.implementer(grades_interfaces.IGrade, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class Grade(SchemaConfigured, CreatedModDateTrackingObject):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	createDirectFieldProperties(grades_interfaces.IGrade)

	@property
	def NTIID(self):
		return self.entry

	def __eq__(self, other):
		try:
			return self is other or (grades_interfaces.IGrade.providedBy(Grade)
									 and self.entry == other.entry)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.entry)
		return xhash

	def __str__(self):
		return "%s,%s" % (self.entry, self.grade)

	def __repr__(self):
		return "%s(%s,%s,%s)" % (self.__class__.__name__, self.entry, self.grade, self.autograde)

@interface.implementer(grades_interfaces.IGrades, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class Grades(PersistentMapping):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass

	def add_grade(self, username, grade):
		grades = self.get(username, None)
		if grades is None:
			grades = self['username'] = BList()
		idx = grades.index(grade)
		if idx == -1:
			grades.append(grade)
		else:
			grades[idx] = grade

	set_grade = add_grade

	def get_grades(self, username):
		grades = self.get(username, None)
		return list(grades) if grades else None

	def remove_grade(self, username, grade):
		result = False
		grades = self.get(username, None)
		if grades:
			if grades_interfaces.IGrade.providedBy(grade):
				grade = grade.NTIID
			idx = -1
			grade = unicode(grade)
			for i, g in enumerate(grades):
				if g.NTIID == grade:
					idx = i
					break
			if idx != -1:
				grades.pop(idx)
				result = True
		return result
