#!/usr/bin/env python
"""
Grading algorithm support.
"""
from __future__ import print_function, unicode_literals

import numbers

from nti.assessment import interfaces
from zope import interface

@staticmethod
def _id(o): return o

class _AbstractGrader(object):
	"""
	"""

	def __init__( self, part, soln, response ):
		self.part = part
		self.solution = soln
		self.response = response

class EqualityGrader(_AbstractGrader):
	"""
	Grader that simply checks for equality using the python equality operator.
	"""
	interface.implements(interfaces.IQPartGrader)

	solution_converter = _id

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

class MatchingPartGrader(_AbstractGrader):
	"""
	Grader that deals with matching. Handles all combinations of int and key solutions
	and int and key dicts.
	"""
	interface.implements(interfaces.IQMatchingPartGrader)

	def _to_int_dict( self, the_dict ):
		result = the_dict
		if not all( (isinstance(x,numbers.Integral) for x in the_dict.keys()) ):
			# Then they must be actual key-value pairs
			try:
				result = { self.part.labels.index(k): self.part.values.index(v)
						   for k, v
						   in the_dict.items() }
			except ValueError:
				# Ooh, too bad. A wrong key/value
				result = {}
		return result

	def __call__( self ):
		rsp_dict = self._to_int_dict( self.response.value )
		soln_dict = self._to_int_dict( self.solution.value )

		return rsp_dict == soln_dict # our numeric score could be how many match
