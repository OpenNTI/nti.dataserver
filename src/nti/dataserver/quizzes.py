#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import collections

import persistent
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList

from zope import interface
import zope.deprecation

from nti.assessment import interfaces as as_interfaces

from nti.dataserver import datastructures

from nti.externalization.datastructures import ExternalizableDictionaryMixin
from nti.externalization.externalization import to_standard_external_dictionary, toExternalObject
from nti.externalization.interfaces import StandardExternalFields, IExternalObject
from nti.externalization import oids

from nti.deprecated import deprecated
import mimetype
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.ntiids import find_object_with_ntiid
from nti.ntiids import ntiids

# TODO: These need interfaces and modeling.

class QuizQuestionAnswer(persistent.Persistent):

	def __init__( self, value=None ):
		super(QuizQuestionAnswer,self).__init__()
		self.value = value

	def setValue( self, value ):
		self.value = value

	def __repr__( self ):
		return "QuizQuestionAnswer('%s')" % self.value

	def __str__( self ):
		return self.value

class QuizQuestion(persistent.Persistent):

	def __init__( self, theId=None, source="" ):
		super(QuizQuestion,self).__init__()
		self.answers = PersistentList()
		self.source = source
		self.id = theId

	def addAnswer( self, answer ):
		self.answers.append( answer )

	def getAnswers(self):
		return self.answers


	def toExternalDictionary( self, mergeFrom=None ):
		result = to_standard_external_dictionary( self, mergeFrom )
		result['Text'] = self.source
		result['Answers'] = toExternalObject( [answer.value for answer in self.answers] )
		return result

class Quiz(datastructures.ZContainedMixin,datastructures.CreatedModDateTrackingObject,persistent.Persistent):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements(nti_interfaces.IModeledContent,IExternalObject)

	canUpdateSharingOnly = True
	__external_can_create__ = True

	def __init__( self ):
		super(Quiz,self).__init__()
		self.questions = PersistentMapping()
		self.id = None

	def __getitem__( self, key ):
		return self.questions[key]

	def getQuestion( self, qid ):
		return self.questions.get( qid, None )

	def clear(self):
		self.questions.clear()
		self.updateLastMod()

	# This entire object is deprecated
	def update( self, rawValue ):
		if isinstance( rawValue, Quiz ):
			self.questions.clear()
			self.questions.update( rawValue.questions )
			return self
		return self.updateFromExternalObject( rawValue )

	def updateFromExternalObject( self, dictionary ):
		self.questions.clear()
		for key, item in dictionary["Items"].iteritems():
			question = QuizQuestion( key, item['Text'] )
			for answer in item['Answers']:
				question.addAnswer( QuizQuestionAnswer( answer ) )
				self.questions[question.id] = question
		self.containerId = dictionary.get( StandardExternalFields.CONTAINER_ID, self.containerId )
		self.updateLastMod()

	@property
	def NTIID(self):
		# TODO: Better NTIID here
		# To grade, we need to be able to look these things up
		# They could be associated with a provider, and we can do the "provider.get_by_ntiid"
		# thing.
		# If we are not stored as an enclosure but a real object, our ID will already be an
		# ntiid, unfortunately of the wrong type (OID instead of Quiz).
		if self.id:
			if ntiids.is_valid_ntiid_string( self.id ):
				return self.id
			if self.creator:
				try:
					return ntiids.make_ntiid( provider=self.creator, nttype=ntiids.TYPE_QUIZ, specific=self.id )
				except ntiids.InvalidNTIIDError:
					pass

		return oids.to_external_ntiid_oid( self )

	def to_container_key( self ):
		return self.NTIID

	def toExternalDictionary( self, mergeFrom=None ):
		result = to_standard_external_dictionary(self, mergeFrom=mergeFrom)

		items = { question.id: question.toExternalDictionary() for question in self.questions.itervalues()}
		result['Items'] = items
		return result


class QuizQuestionResponse(persistent.Persistent):
	interface.implements(as_interfaces.IQTextResponse)

	def __init__(self, quizId=None, theId=None, actualValue=None):
		super(QuizQuestionResponse,self).__init__()
		self.quizId = quizId
		self.id = theId
		self.actualValue = actualValue

	def setResponse( self, actualValue ):
		self.actualValue = actualValue

	def getResponse(self):
		return self.actualValue

	response = property(getResponse, setResponse)
	value = property(getResponse,setResponse) # For compliance with IQTextResponse

	def __repr__( self ):
		return "QuizQuestionResponse('%s')" % self.actualValue

	def __str__( self ):
		return self.actualValue

from nti.assessment import assess

class QuizResult(datastructures.ZContainedMixin,
				 datastructures.CreatedModDateTrackingObject,
				 persistent.Persistent,
				 ExternalizableDictionaryMixin):

	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	interface.implements(nti_interfaces.IModeledContent,IExternalObject)

	__external_can_create__ = True

	QuizID = None

	def __init__(self, quizId=None, theId=None):
		super(QuizResult,self).__init__( containedId=theId )
		self.assessments = PersistentMapping()

	def addAssessment( self, question, response, assesment ):
		self.assessments[question.id if hasattr(question, 'id') else question] = (question,response,assesment)
		self.updateLastMod()

	def updateFromExternalObject( self, rawValue, dataserver=None ):
		# Only fresh objects can be updated
		# if getattr( self, '_p_jar', None ):
		#	raise ValueError( "Can only update new results." )
		# TODO: If that's a desired condition, then don't implement it with
		# _p_jar, which is not reliable. Change the ACL

		self.containerId = rawValue.get( StandardExternalFields.CONTAINER_ID, self.containerId )

		quizId = rawValue.get( 'QuizID' )
		if not quizId:
			quizId = rawValue[StandardExternalFields.CONTAINER_ID] if StandardExternalFields.CONTAINER_ID in rawValue else self.containerId

		# Backwards compat warnings
		if not StandardExternalFields.CONTAINER_ID in rawValue or not "QuizID" in rawValue:
			logger.warning( "Please provide container id and quiz id" )

		# If we have arrived at a quiz id that is an NTIID, but /NOT/ on OID or Quiz NTIID,
		# then this probably means we're using the container id. This allows for an
		# easy one-to-one mapping between containers-as-pages and quizzes.
		if ntiids.is_valid_ntiid_string( quizId ) \
			and not ntiids.is_ntiid_of_type( quizId, ntiids.TYPE_OID ) \
			and not ntiids.is_ntiid_of_type( quizId, ntiids.TYPE_QUIZ ):

			quizId = ntiids.make_ntiid( base=quizId, nttype=ntiids.TYPE_QUIZ )

		self.QuizID = quizId

		rawValue = self.stripSyntheticKeysFromExternalDictionary( rawValue )
		qqRs = {}

		# Support both "raw" dictionaries of key: response
		# and wrapped class-like dictionaries
		iterover = rawValue['Items'] if 'Items' in rawValue else rawValue
		# The old format was to send dictionaries of trivial things
		if isinstance(iterover, collections.Mapping ):
			for key, value in iterover.iteritems():
				if isinstance( value, collections.Mapping ) and 'Response' in value:
					value = value['Response']
				qqr = QuizQuestionResponse( quizId, key, value )
				qqRs[key] = qqr
		else:
			# The new format matches the output format
			for qqr in iterover:
				if isinstance( qqr, collections.Mapping ):
					qqr = QuizQuestionResponse( quizId, qqr['ID'], qqr['Response'] )
				qqRs[qqr.id] = qqr
				# TODO: Handle multiple submissions

		# FIXME: Looking up the quiz is being handled in a weird way.
		# We begin by looking
		quiz = find_object_with_ntiid( quizId )
		if not quiz:
			# FIXME: This double nesting is weird ard wrong. QuizTree sets things up funny.
			quiz = dataserver.root.get('quizzes', {}).get('quizzes', {}).get(quizId)
		if not quiz:
			raise ValueError( "Unable to locate quiz " + str(quizId ) )
		__traceback_info__ = quiz, qqRs
		theAssessments = assess( quiz, qqRs )
		for qqR in qqRs.itervalues():
			assessment = theAssessments[qqR.id]
			self.addAssessment( quiz.getQuestion( qqR.id ), qqR, assessment )

		return self

	update = updateFromExternalObject

	def toExternalDictionary( self, mergeFrom=None ):
		result = to_standard_external_dictionary( self, mergeFrom=mergeFrom )
		result['QuizID'] = self.QuizID

		items = []
		for q, r, a in self.assessments.itervalues():
			# If the student didn't respond at all, don't send
			# back the right answer (by request of MC)
			question = q.toExternalDictionary()
			if not r.response:
				question['Answers'] = []
			question = toExternalObject( question )
			items.append( { "Question": question,
							"Response": r.response,
							"Assessment": a,
							# Notice we're hijacking the name of the existing class,
							# since we externalize on its behalf
							"Class": "QuizQuestionResponse"} )
		result['Items'] = items
		return result

zope.deprecation.deprecated( "Quiz", "Prefer the nti.assessment package." )
