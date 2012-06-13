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

@interface.implementer(interfaces.IQAssessedPart)
class QAssessedPart(persistent.Persistent):
	submittedResponse = None
	assessedValue = 0.0

QAssessedPart.__init__ = _make_init(QAssessedPart)
QAssessedPart.__repr__ = make_repr()

@interface.implementer(interfaces.IQAssessedQuestion)
class QAssessedQuestion(persistent.Persistent):
	questionId = None
	parts = ()

QAssessedQuestion.__init__ = _make_init(QAssessedQuestion)
QAssessedQuestion.__repr__ = make_repr()


@interface.implementer(interfaces.IQAssessedQuestionSet)
class QAssessedQuestionSet(persistent.Persistent):
	questionSetId = None
	questions = ()

QAssessedQuestionSet.__init__ = _make_init(QAssessedQuestionSet)
QAssessedQuestionSet.__repr__ = make_repr()
