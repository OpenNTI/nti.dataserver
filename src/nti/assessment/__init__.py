#!/usr/bin/env python2.7

import plasTeX

from _latexplastexconverter import _response_text_to_latex
from _latexplastexconverter import _mathTexToDOMNodes as mathTexToDOMNodes
from _latexplastexdomcompare import _mathIsEqual as mathIsEqual

import solution

from zope.deprecation import deprecated

def grade_one_response(questionResponse, possible_answers):
	"""
	:param questionResponse: The string to evaluate. It may be in latex notation
		or openmath XML notation, or plain text. We may edit the response
		to get something parseable.
	:param list possible_answers: A sequence of possible answers to compare
		`questionResponse` with.
	"""

	answers = [solution.QLatexSymbolicMathSolution( t ) for t in possible_answers]

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

#deprecated( "assess", "Prefer ???")
