#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Having to do with submitting external data for grading.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import


logger = __import__('logging').getLogger(__name__)


from zope import interface
from zope import component
import persistent
import persistent.list

from nti.utils.schema import PermissiveSchemaConfigured as SchemaConfigured
from nti.externalization.externalization import make_repr
# EWW...but we need to be IContained in order to be stored
# in container data structures.
# We also want to be ILastModified
# so that we can cheaply store and access lastmodified times
# without going through the expense of ZopeDublinCore (since we expect no other
# annotations and no mutability)
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

	def __hash__( self ):
		return hash((self.submittedResponse, self.assessedValue))

from zope.datetime import parseDatetimetz
import time
def _dctimes_property_fallback(attrname, dcname):
	# For BWC, if we happen to have annotations that happens to include
	# zope dublincore data, we will use it
	# TODO: Add a migration to remove these
	def get(self):
		self._p_activate() # make sure there's a __dict__
		if attrname in self.__dict__:
			return self.__dict__[attrname]

		if '__annotations__' in self.__dict__:
			try:
				dcdata = self.__annotations__['zope.app.dublincore.ZopeDublinCore']
				date_modified = dcdata[dcname] # tuple of a string
				datetime = parseDatetimetz( date_modified[0] )
				return time.mktime( datetime.timetuple() )
			except KeyError:
				pass

		return 0

	def _set(self,value):
		self.__dict__[attrname] = value

	return property(get, _set)

@interface.implementer(interfaces.IQAssessedQuestion, nti_interfaces.IContained, nti_interfaces.IZContained, nti_interfaces.ICreated, nti_interfaces.ILastModified)
class QAssessedQuestion(SchemaConfigured,persistent.Persistent):
	questionId = None
	parts = ()
	creator = None
	id = None
	containerId = None
	__name__ = None
	__parent__ = None
	__external_can_create__ = False

	createdTime = _dctimes_property_fallback('createdTime', 'Date.Modified')
	lastModified = _dctimes_property_fallback('lastModified', 'Date.Created')
	def updateLastMod(self, t=None ):
		self.lastModified = ( t if t is not None and t > self.lastModified else time.time() )
		return self.lastModified

	def __init__( self, *args, **kwargs ):
		super(QAssessedQuestion,self).__init__( *args, **kwargs )
		self.lastModified = self.createdTime = time.time()

	def __eq__( self, other ):
		try:
			return self is other or (self.questionId == other.questionId
									 and self.parts == other.parts)
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		return not self == other

	__repr__ = make_repr()

	def __hash__(self):
		return hash( (self.questionId, tuple(self.parts)) )


@interface.implementer(interfaces.IQAssessedQuestionSet, nti_interfaces.IContained, nti_interfaces.IZContained, nti_interfaces.ICreated, nti_interfaces.ILastModified)
class QAssessedQuestionSet(SchemaConfigured,persistent.Persistent):
	questionSetId = None
	questions = ()
	creator = None
	id = None
	containerId = None
	__name__ = None
	__parent__ = None
	__external_can_create__ = False

	createdTime = _dctimes_property_fallback('createdTime', 'Date.Modified')
	lastModified = _dctimes_property_fallback('lastModified', 'Date.Created')
	def updateLastMod(self, t=None ):
		self.lastModified = ( t if t is not None and t > self.lastModified else time.time() )
		return self.lastModified

	def __init__( self, *args, **kwargs ):
		super(QAssessedQuestionSet,self).__init__( *args, **kwargs )
		self.lastModified = self.createdTime = time.time()


	def __eq__( self, other ):
		try:
			return self is other or (self.questionSetId == other.questionSetId
									 and self.questions == other.questions)
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		return not self == other

	__repr__ = make_repr()

	def __hash__(self):
		return hash( (self.questionSetId, tuple(self.questions)) )


def assess_question_submission( submission, questions=None ):
	"""
	Assess the given question submission.

	:return: An :class:`.interfaces.IQAssessedQuestion`.
	:param submission: An :class:`.interfaces.IQuestionSubmission`.
	:param questions: If given, an :class:`.interfaces.IQuestionMap`. If
		not given, one will be looked up from the component registry.
	:raises KeyError: If no question can be found for the submission.
	"""

	if questions is None:
		questions = component.getUtility( interfaces.IQuestionMap )

	question = questions[submission.questionId]
	if len(question.parts) != len(submission.parts):
		raise ValueError( "Question (%s) and submission (%s) have different numbers of parts." % ( len(question.parts), len(submission.parts) ) )

	assessed_parts = persistent.list.PersistentList()
	for sub_part, q_part in zip( submission.parts, question.parts ):
		grade = q_part.grade( sub_part )
		assessed_parts.append( QAssessedPart( submittedResponse=sub_part, assessedValue=grade ) )

	return QAssessedQuestion( questionId=submission.questionId, parts=assessed_parts )

def assess_question_set_submission( set_submission, questions=None ):
	"""
	Assess the given question set submission.

	:return: An :class:`.interfaces.IQAssessedQuestionSet`.
	:param set_submission: An :class:`.interfaces.IQuestionSetSubmission`.
	:param questions: If given, an :class:`.interfaces.IQuestionMap`. If
		not given, one will be looked up from the component registry.
	:raises KeyError: If no question can be found for the submission.
	"""

	if questions is None:
		questions = component.getUtility( interfaces.IQuestionMap )

	question_set = questions[set_submission.questionSetId]
	# NOTE: At this point we need to decide what to do for missing values
	# We are currently not really grading them at all, which is what we
	# did for the old legacy quiz stuff

	assessed = persistent.list.PersistentList()
	for sub_question in set_submission.questions:
		question = questions[sub_question.questionId]
		# FIXME: Checking an 'ntiid' property that is not defined here is a hack
		# because we have an equality bug. It should go away as soon as equality is fixed
		if question in question_set.questions or getattr( question, 'ntiid', None) in [getattr(q, 'ntiid', None) for q in question_set.questions]:
			assessed.append( interfaces.IQAssessedQuestion( sub_question ) )
		else:
			logger.debug( "Bad input, question (%s) not in question set (%s) (kownn: %s)", question, question_set, question_set.questions )

	# NOTE: We're not really creating some sort of aggregate grade here
	return QAssessedQuestionSet( questionSetId=set_submission.questionSetId, questions=assessed )
