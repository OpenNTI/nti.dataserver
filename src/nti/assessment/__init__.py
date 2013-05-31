#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import unicode_literals, print_function, absolute_import
__docformat__ = "restructuredtext en"

from . import interfaces

def grade_one_response(questionResponse, possible_answers):
	"""
	:param questionResponse: The string to evaluate. It may be in latex notation
		or openmath XML notation, or plain text. We may edit the response
		to get something parseable.
	:param list possible_answers: A sequence of possible answers to compare
		`questionResponse` with.
	"""

	answers = [interfaces.IQLatexSymbolicMathSolution(t) for t in possible_answers]

	match = False
	for answer in answers:
		match = answer.grade(questionResponse)
		if match:
			return match

	return False

def assess(quiz, responses):
	result = {}
	for questionId, questionResponse in responses.iteritems():
		result[questionId] = grade_one_response(questionResponse, quiz[questionId].answers)
	return result
