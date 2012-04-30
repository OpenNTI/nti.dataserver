#!/usr/bin/env python2.7

import plasTeX

from _latexplastexconverter import _response_text_to_latex
from _latexplastexconverter import _mathTexToDOMNodes as mathTexToDOMNodes
from _latexplastexdomcompare import _mathIsEqual as mathIsEqual

def grade_one_response(questionResponse, possible_answers):
	"""
	:param questionResponse: The string to evaluate. It may be in latex notation
		or openmath XML notation, or plain text. We may edit the response
		to get something parseable.
	:param list possible_answers: A sequence of possible answers to compare
		`questionResponse` with.
	"""
	answers = mathTexToDOMNodes( possible_answers )
	response = str(questionResponse)
	if not response:
		#The student skipped this question. Always
		#a fail.
		return False

	response_doc = _response_text_to_latex( response )
	response = mathTexToDOMNodes( ( response_doc, ) )

	if len(response) != 1:
		# TODO: How to handle this? We need to present
		# some sort of retry condition?
		raise Exception( u"Invalid response format '%s' (%s/%s -> %s/%s)" % (questionResponse, response_doc, type(response_doc), len(response), response) )

	match = False
	for answer in answers:
		for rsp in response:
			match = mathIsEqual( rsp, answer )
			if match:
				return True

	return False

def assess( quiz, responses ):
	result = {}
	for questionId, questionResponse in responses.iteritems():
		result[questionId] = grade_one_response( questionResponse, quiz[questionId].answers )
	return result
