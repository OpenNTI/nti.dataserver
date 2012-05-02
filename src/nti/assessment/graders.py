#!/usr/bin/env python
"""
Grading algorithm support.
"""
from __future__ import print_function, unicode_literals

from nti.assessment import interfaces
from zope import interface

@staticmethod
def _id(o): return o

class EqualityGrader(object):
	"""
	Grader that simply checks for equality using the python equality operator.
	"""
	interface.implements(interfaces.IQPartGrader)

	solution_converter = _id

	def __init__( self, part, soln, response ):
		self.part = part
		self.solution = soln
		self.response = response

	def __call__( self ):
		return self.solution.value == self.solution_converter(self.response.value)

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

class MultipleChoiceGrader(EqualityGrader):
	"""
	Grader that grades multiple choice questions by
	checking to see if the given value matches the solution
	value (they should both be indices, but this allows choices
	to be stored as a map and the solution be a key). If this fails,
	then we check to see if the given response is in the possible
	choices (allowing submission of the actual data, which may be
	convenient in some cases).
	"""

	interface.implements(interfaces.IQMultipleChoicePartGrader)

	def __call__(self):
		result = super(MultipleChoiceGrader,self).__call__()
		if not result:
			index = None
			try:
				index = self.part.choices.index( self.response.value )
			except ValueError:
				result = False
			else:
				result = index == self.solution.value

		return result
