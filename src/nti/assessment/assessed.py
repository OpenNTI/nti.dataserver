#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Having to do with submitting external data for grading.

$Id$
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component
import persistent

from nti.utils.schema import PermissiveSchemaConfigured as SchemaConfigured
from nti.externalization.externalization import make_repr
# EWW...but we need to be IContained in order to be stored
# in container data structures
from nti.dataserver import interfaces as nti_interfaces

from . import interfaces


@interface.implementer(interfaces.IQAssessedPart)
class QAssessedPart(SchemaConfigured,persistent.Persistent):
	submittedResponse = None
	assessedValue = 0.0
	__external_can_create__ = False

	def __eq__( self, other ):
		try:
			return self is other or (self.submittedResponse == other.submittedResponse
								 and self.assessedValue == other.assessedValue)
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		return not self == other

	__repr__ = make_repr()

@interface.implementer(interfaces.IQAssessedQuestion, nti_interfaces.IContained, nti_interfaces.IZContained, nti_interfaces.ICreated)
class QAssessedQuestion(SchemaConfigured,persistent.Persistent):
	questionId = None
	parts = ()
	creator = None
	id = None
	containerId = None
	__name__ = None
	__parent__ = None
	__external_can_create__ = False

	def __eq__( self, other ):
		try:
			return self is other or (self.questionId == other.questionId
									 and self.parts == other.parts)
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		return not self == other

	__repr__ = make_repr()


@interface.implementer(interfaces.IQAssessedQuestionSet, nti_interfaces.IContained, nti_interfaces.IZContained, nti_interfaces.ICreated)
class QAssessedQuestionSet(SchemaConfigured,persistent.Persistent):
	questionSetId = None
	questions = ()
	creator = None
	id = None
	containerId = None
	__name__ = None
	__parent__ = None
	__external_can_create__ = False


	def __eq__( self, other ):
		try:
			return self is other or (self.questionSetId == other.questionSetId
									 and self.questions == other.questions)
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		return not self == other

	__repr__ = make_repr()


def assess_question_submission( submission, questions=None ):
	"""
	Assess the given question submission.
	:return: An :class:`interfaces.IQAssessedQuestion`.
	:param questions: If given, an :class:`interfaces.IQuestionMap`. If
		not given, one will be looked up from the component registry.
	:raises KeyError: If no question can be found for the submission.
	"""

	if questions is None:
		questions = component.getUtility( interfaces.IQuestionMap )

	question = questions[submission.questionId]
	if len(question.parts) != len(submission.parts):
		raise ValueError( "Question and submission have different numbers of parts." )

	assessed_parts = []
	for sub_part, q_part in zip( submission.parts, question.parts ):
		grade = q_part.grade( sub_part )
		assessed_parts.append( QAssessedPart( submittedResponse=sub_part, assessedValue=grade ) )

	return QAssessedQuestion( questionId=submission.questionId, parts=assessed_parts )

def assess_question_set_submission( set_submission, questions=None ):
	"""
	Assess the given question set submission.
	:return: An :class:`interfaces.IQAssessedQuestionSet`.
	:param questions: If given, an :class:`interfaces.IQuestionMap`. If
		not given, one will be looked up from the component registry.
	:raises KeyError: If no question can be found for the submission.
	"""

	if questions is None:
		questions = component.getUtility( interfaces.IQuestionMap )

	question_set = questions[set_submission.questionSetId]
	# NOTE: At this point we need to decide what to do for missing values
	# We are currently not really grading them at all, which is what we
	# did for the old legacy quiz stuff

	assessed = []
	for sub_question in set_submission.questions:
		question = questions[sub_question.questionId]
		if question in question_set.questions:
			assessed.append( interfaces.IQAssessedQuestion( sub_question ) )

	# NOTE: We're not really creating some sort of aggregate grade here
	return QAssessedQuestionSet( questionSetId=set_submission.questionSetId, questions=assessed )
