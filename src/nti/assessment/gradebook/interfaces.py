#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id: interfaces.py 19693 2013-05-30 23:06:02Z carlos.sanchez $
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.utils import schema as dmschema

class IGradeBookEntry(interface.Interface):
	name = dmschema.ValidTextLine(title="entry name", required=True)
	weight = schema.Float(title="The relative weight of this entry, from 0 to 1",
						  min=0.0,
						  max=1.0,
						  default=1.0)

class IGradeBookPart(interface.Interface):
	"""
	A Section of a grade book e.g. Quizzes, Exams, etc..
	"""
	name = dmschema.ValidTextLine(title="Part name", required=True)

	parts = dmschema.ListOrTuple(title="Grade item",
								 required=True, min_length=0,
			     				 value_type=schema.Object(IGradeBookEntry, title="The grade entry"))

	weight = schema.Float(title="The relative weight of this part, from 0 to 1",
						  min=0.0,
						  max=1.0,
						  default=1.0)

class IGradeBook(interface.Interface):
	"""
	Grade book definition
	"""
	parts = dmschema.ListOrTuple(title="Grade book part",
								 required=True, min_length=1,
			     				 value_type=schema.Object(IGradeBookPart, title="The part"))

