#!/usr/bin/env python
"""
Grading algorithm support.
"""
from __future__ import print_function, unicode_literals

import numbers

from zope import interface

from nti.assessment import interfaces


@staticmethod
def _id(o): return o

@staticmethod
def _lower(o): return unicode(o).lower()

class _AbstractGrader(object):
	"""
	Base class for IQPartGrader objects. These are
	expected to be registered as a multi-adapter
	on the part, solution, and response type, thus
	allowing for a great deal of flexibility in determining
	a grader for any combination of inputs.
	"""

	def __init__( self, part, solution, response ):
		self.part = part
		self.solution = solution
		self.response = response

	def __call__( self ):
		raise NotImplementedError()

@interface.implementer(interfaces.IQPartGrader)
class EqualityGrader(_AbstractGrader):
	"""
	Grader that simply checks for equality using the python equality operator.
	"""

	#: This factory function is called on the value of the response
	#: before checking for equality.
	solution_converter = _id

	def __call__( self ):
		return self._compare( self.solution.value, self.response.value )

	def _compare( self, solution_value, response_value ):
		return solution_value == self.solution_converter(response_value)

class StringEqualityGrader(EqualityGrader):
	"""
	Grader that converts the response to a string before doing
	an equality comparison.
	"""
	solution_converter = unicode

class LowerStringEqualityGrader(StringEqualityGrader):
	"""
	Grader that converts the response to a lowercase string
	before doing an equality comparison.
	"""
	solution_converter = _lower

class FloatEqualityGrader(EqualityGrader):
	"""
	Grader that converts the response to a number before
	doing an equality comparison.
	"""
	solution_converter = float

class UnitAwareFloatEqualityGrader(FloatEqualityGrader):
	"""
	A grader that handles dealing with units in responses.

	The solution type this is registered for must be an :class:`.IQMathSolution`
	"""

	def __call__( self ):
		if self.solution.allowed_units is None: # No special unit handling
			return super(UnitAwareFloatEqualityGrader,self).__call__()

		if not self.solution.allowed_units: # Units are specifically forbidden
			# Then the response must parse cleanly as a floating point number,
			# which happens to be the default behaviour
			try:
				return super(UnitAwareFloatEqualityGrader,self).__call__()
			except ValueError:
				# Failed to parse. Unlike in the default case, we do have an opinion,
				# this isn't faulty input and is a wrong answer
				return False

		# Units may be required, or optional if the last element is the empty string
		for unit in self.solution.allowed_units:
			if self.response.value.endswith( unit ):
				# strip the trailing unit and grade.
				# This handles unit='cm' and value in ('1.0 cm', '1.0cm')
				# It also handles unit='', if it comes at the end
				value = self.response.value[:-len(unit)] if unit else self.response.value
				__traceback_info__ = self.response.value, unit, value
				return self._compare( self.solution.value, value )

		# If we get here, there was no unit that matched. Therefore, units were required
		# and not given
		return False

@interface.implementer(interfaces.IQMultipleChoicePartGrader)
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

	def __call__(self):
		# Does it exactly match?
		result = super(MultipleChoiceGrader,self).__call__()
		if not result:
			# No. Ok, did they send us the actual value?
			index = None
			try:
				index = self.part.choices.index( self.response.value )
			except ValueError:
				# The value they sent isn't present. Maybe they sent an
				# int string?
				try:
					index = int( self.response.value )
					# They sent an int. We can take this, if the actual value they sent
					# is not an option. If the choices are "0", "2", "3", with index 1, value "2"
					# being correct, and they send "1", we shouldn't accept that
					# TODO: Handle that case. Fortunately, it's a corner case
				except ValueError:
					# Nope, not an int. So this won't match
					index = None



			result = (index == self.solution.value)

		return result

@interface.implementer(interfaces.IQMultipleChoiceMultipleAnswerPartGrader)
class MultipleChoiceMultipleAnswerGrader(EqualityGrader):
	"""
	Grader that grades multiple choice / multiple answer questions by
	checking to see if the given list of values matches the solution
	value list (they should both be lists of indices, but this allows
	choices to be stored as a map and the elements of the solution list
	to be a key).
	"""


@interface.implementer(interfaces.IQMatchingPartGrader)
class MatchingPartGrader(_AbstractGrader):
	"""
	Grader that deals with matching. Handles all combinations of int and key solutions
	and int and key dicts.
	"""

	def _to_int_dict( self, the_dict ):
		result = the_dict
		if not all( (isinstance(x,numbers.Integral) for x in the_dict.keys()) ):
			# Then they must be actual key-value pairs
			try:
				result = { self.part.labels.index(k): self.part.values.index(v)
						   for k, v
						   in the_dict.items() }
			except ValueError:
				# Try string to int conversion
				try:
					result = { int(k) : int(v) for k,v in the_dict.items() }
				except ValueError:
					# Ooh, too bad. A wrong key/value
					result = {}
		return result

	def __call__( self ):
		rsp_dict = self._to_int_dict( self.response.value )
		soln_dict = self._to_int_dict( self.solution.value )

		return rsp_dict == soln_dict # our numeric score could be how many match
