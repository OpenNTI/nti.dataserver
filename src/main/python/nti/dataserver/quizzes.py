#!/usr/bin/env python2.7


import collections

import persistent
from persistent.mapping import PersistentMapping
from persistent.list import PersistentList

from datastructures import  ExternalizableDictionaryMixin, CreatedModDateTrackingObject, toExternalObject, toExternalDictionary
import datastructures

from nti.deprecated import deprecated

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
		result = toExternalDictionary( self, mergeFrom )
		result['Text'] = self.source
		result['Answers'] = toExternalObject( [answer.value for answer in self.answers] )
		return result

class Quiz(CreatedModDateTrackingObject,persistent.Persistent):

	def __init__( self ):
		super(Quiz,self).__init__()
		self.questions = PersistentMapping()
		self.id = None

	def __getitem__( self, key ):
		if key in self.questions:
			return self.questions[key]
		return super(Quiz,self).__getitem__(key)

	def getQuestion( self, qid ):
		return self.questions.get( qid, None )

	def clear(self):
		self.questions.clear()
		self.updateLastMod()

	@deprecated()
	def update( self, rawValue ):
		return self.updateFromExternalObject( rawValue )

	def updateFromExternalObject( self, dictionary ):
		self.questions.clear()
		for key, item in dictionary["Items"].iteritems():
			question = QuizQuestion( key, item['Text'] )
			for answer in item['Answers']:
				question.addAnswer( QuizQuestionAnswer( answer ) )
				self.questions[question.id] = question
		self.updateLastMod()

	def toExternalDictionary( self, mergeFrom=None ):
		result = toExternalDictionary(self, mergeFrom=mergeFrom)

		items = { question.id: question.toExternalDictionary() for question in self.questions.itervalues()}
		result['Items'] = items
		return result


class QuizQuestionResponse(persistent.Persistent):

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

	def __repr__( self ):
		return "QuizQuestionResponse('%s')" % self.actualValue

	def __str__( self ):
		return self.actualValue

from nti.assessment import assess

class QuizResult(datastructures.ContainedMixin,CreatedModDateTrackingObject,persistent.Persistent,ExternalizableDictionaryMixin):

	__external_can_create__ = True

	def __init__(self, quizId=None, theId=None):
		super(QuizResult,self).__init__( )
		self.id = theId
		self.assessments = PersistentMapping()

	def addAssessment( self, question, response, assesment ):
		self.assessments[question.id if hasattr(question, 'id') else question] = (question,response,assesment)
		self.updateLastMod()

	@deprecated()
	def update( self, rawValue ):
		return self.updateFromExternalObject( rawValue )

	def updateFromExternalObject( self, rawValue, dataserver=None ):
		# Only fresh objects can be updated
		if getattr( self, '_p_jar', None ):
			raise ValueError( "Can only update new results." )
		rawValue = self.stripSyntheticKeysFromExternalDictionary( rawValue )
		quizId = rawValue['ContainerID'] if 'ContainerID' in rawValue else self.containerId
		qqRs = {}

		# Support both "raw" dictionaries of key: response
		# and wrapped class-like dictionaries
		iterover = rawValue['Items'] if 'Items' in rawValue else rawValue

		for key, value in iterover.iteritems():
			if isinstance( value, collections.Mapping ) and 'Response' in value:
				value = value['Response']
			qqr = QuizQuestionResponse( quizId, key, value )
			qqRs[key] = qqr

		# FIXME: This double nesting is weird ard wrong. QuizTree sets things up funny.
		quiz = dataserver.root['quizzes']['quizzes'][quizId]
		theAssessments = assess( quiz, qqRs )
		for qqR in qqRs.itervalues():
			assessment = theAssessments[qqR.id]
			self.addAssessment( quiz.getQuestion( qqR.id ), qqR, assessment )

		return self

	def toExternalDictionary( self, mergeFrom=None ):
		result = toExternalDictionary( self, mergeFrom=mergeFrom )
		result['QuizID'] = self.containerId

		items = []
		for q,r,a in self.assessments.itervalues():
			items.append( { "Question": toExternalObject( q.toExternalDictionary() ),
							"Response": r.response,
							"Assessment": a,
							# Notice we're hijacking the name of the existing class,
							# since we externalize on its behalf
							"Class": "QuizQuestionResponse"} )
		result['Items'] = items
		return result

