#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.container import contained

from nti.externalization.persistence import NoPickle
from nti.externalization.externalization import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createFieldProperties

from .interfaces import ICredit
from .interfaces import ICourseInfo
from .interfaces import IEnrollment
from .interfaces import IInstructor
from .interfaces import IPrerequisite

@interface.implementer(IInstructor)
@WithRepr
@NoPickle
@EqHash ('name', 'title')
class Instructor(SchemaConfigured, contained.Contained):
	createFieldProperties(IInstructor)

	__external_can_create__ = True
	__external_class_name__ = "Instructor"
	mime_type = mimeType = 'application/vnd.nextthought.courseinfo.instructor'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IPrerequisite)
@WithRepr
@NoPickle
@EqHash('id', 'title')
class Prerequisite(SchemaConfigured, contained.Contained):
	createFieldProperties(IPrerequisite)

	__external_can_create__ = True
	__external_class_name__ = 'Prerequisite'
	mime_type = mimeType = 'application/vnd.nextthought.prerequisite'

	def __init__ (self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(IEnrollment)
@WithRepr
@NoPickle
@EqHash('label', 'url')
class Enrollment(SchemaConfigured, contained.Contained):
	createFieldProperties(IEnrollment)

	__external_can_create__ = True
	__external_class_name__ = 'Enrollment'
	mime_type = mimeType = 'application/vnd.nextthought.enrollment'

	def __init__ (self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(ICredit)
@WithRepr
@NoPickle
@EqHash('hours', 'enrollment')
class Credit(SchemaConfigured, contained.Contained):
	createFieldProperties(ICredit)

	__external_can_create__ = True
	__external_class_name__ = 'Credit'
	mime_type = mimeType = 'application/vnd.nextthought.credit'

	def __init__ (self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)

@interface.implementer(ICourseInfo)
@WithRepr
@NoPickle
@EqHash('ntiid', 'id', 'school')
class CourseInfo(SchemaConfigured, contained.Contained):
	createFieldProperties(ICourseInfo)

	__external_can_create__ = True
	__external_class_name__ = "CourseInfo"
	mime_type = mimeType = 'application/vnd.nextthought.courseinfo'

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
