#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: interfaces.py 19693 2013-05-30 23:06:02Z carlos.sanchez $
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope.container.constraints import contains, containers
from zope.container.interfaces import IContainer, IContained

from nti.utils import schema as dmschema

class IGradeBookEntry(IContained):

	containers(b'.IGradeBookPart')

	NTIID = dmschema.ValidTextLine(title="entry ntiid", required=True)
	questionSetID = dmschema.ValidTextLine(title="question id", required=False)
	name = dmschema.ValidTextLine(title="entry name", required=True)
	weight = schema.Float(title="The relative weight of this entry, from 0 to 1",
						  min=0.0,
						  max=1.0,
						  default=1.0)

	order = schema.Int(title="The entry order", min=1)

class IGradeBookPart(IContainer, IContained):
	"""
	A Section of a grade book e.g. Quizzes, Exams, etc..
	"""
	containers(b'.IGradeBook')
	contains(IGradeBookEntry)
	__parent__.required = False

	name = dmschema.ValidTextLine(title="Part name", required=True)

	weight = schema.Float(title="The relative weight of this part, from 0 to 1",
						  min=0.0,
						  max=1.0,
						  default=1.0,
						  required=True)

	order = schema.Int(title="The part order", min=1)

class IGradeBook(IContainer, IContained):
	"""
	Grade book definition
	"""
	contains(IGradeBookPart)
	__parent__.required = False


