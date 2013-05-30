#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Having to do with submitting external data for grading.

$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from dm.zope.schema.schema import SchemaConfigured

from nti.externalization.externalization import make_repr

from nti.assessment import interfaces

@interface.implementer(interfaces.IQuestionSubmission)
class QuestionSubmission(SchemaConfigured):
	questionId = None
	parts = ()

	__repr__ = make_repr()

@interface.implementer(interfaces.IQuestionSetSubmission)
class QuestionSetSubmission(SchemaConfigured):
	questionSetId = None
	questions = ()
	__repr__ = make_repr()
