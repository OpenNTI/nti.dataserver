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


from . import interfaces

def _make_init( cls ):
	"""
	Returns an init method for cls that takes keyword arguments for the attributes of the
	object. Assumes that the class or instance will have already set up attributes to match
	incoming keyword names.
	"""
	def __init__( self, **kwargs ):
		super( cls, self ).__init__()
		for k, v in kwargs.items():
			if v is not None and hasattr( self, k ):
				setattr( self, k, v )

	return __init__


@interface.implementer(interfaces.IQuestionSubmission)
class QuestionSubmission(object):
	questionId = None
	parts = ()

QuestionSubmission.__init__ = _make_init(QuestionSubmission)
QuestionSubmission.__repr__ = make_repr()

@interface.implementer(interfaces.IQuestionSetSubmission)
class QuestionSetSubmission(object):
	questionSetId = None
	questions = ()

QuestionSetSubmission.__init__ = _make_init(QuestionSetSubmission)
QuestionSetSubmission.__repr__ = make_repr()
