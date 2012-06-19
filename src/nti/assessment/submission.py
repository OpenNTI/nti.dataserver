#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Having to do with submitting external data for grading.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
import persistent

from nti.externalization.externalization import make_repr

from dm.zope.schema.schema import SchemaConfigured
from . import interfaces

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
