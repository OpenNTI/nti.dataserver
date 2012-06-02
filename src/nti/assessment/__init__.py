#!/usr/bin/env python

from __future__ import print_function, unicode_literals


from . import interfaces

def grade_one_response(questionResponse, possible_answers):
	"""
	:param questionResponse: The string to evaluate. It may be in latex notation
		or openmath XML notation, or plain text. We may edit the response
		to get something parseable.
	:param list possible_answers: A sequence of possible answers to compare
		`questionResponse` with.
	"""

	answers = [interfaces.IQLatexSymbolicMathSolution( t ) for t in possible_answers]

	match = False
	for answer in answers:
		match = answer.grade( questionResponse )
		if match:
			return match

	return False

def assess( quiz, responses ):
	result = {}
	for questionId, questionResponse in responses.iteritems():
		result[questionId] = grade_one_response( questionResponse, quiz[questionId].answers )
	return result

#from zope.deprecation import deprecated
#deprecated( "assess", "Prefer ???")
