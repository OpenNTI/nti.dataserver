#!/usr/bin/env python
"""
Grading algorithm support.
"""
from __future__ import print_function, unicode_literals
import sys

from nti.assessment import interfaces
from zope import interface

def _id(o): return o

class EqualityGrader(object):
	"""
	Grader that simply checks for equality using the python equality operator.
	"""
	interface.implements(interfaces.IQSolutionResponseGrader)

	solution_converter = _id

	def __init__( self, soln, response ):
		pass

	def grade( self, solution, response ):
		return solution.value == self.solution_converter(response.value)

class StringEqualityGrader(EqualityGrader):
	"""
	Grader that converts the response to a string before doing
	an equality comparison.
	"""
	solution_converter = unicode

class FloatEqualityGrader(EqualityGrader):
	"""
	Grader that converts the response to a number before
	doing an equality comparison.
	"""
	solution_converter = float
