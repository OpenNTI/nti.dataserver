#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Code related to the question interfaces.
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope.mimetype import interfaces as mime_interfaces

from persistent import Persistent

from . import interfaces

@interface.implementer(interfaces.IQuestion,mime_interfaces.IContentTypeAware)
class QQuestion(Persistent):
	mime_type = 'application/vnd.nextthought.naquestion'

	content = ''
	parts = ()

	def __init__( self, content=None, parts=None ):
		if content:
			self.content = content
		if parts:
			self.parts = parts

@interface.implementer(interfaces.IQuestionSet, mime_interfaces.IContentTypeAware)
class QQuestionSet(Persistent):
	mime_type = 'application/vnd.nextthought.naquestionset'

	questions = ()

	def __init__( self, questions=None ):
		if questions:
			self.questions = questions
