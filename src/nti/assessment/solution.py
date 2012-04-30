#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from zope import interface

from nti.assessment import interfaces

from persistent import Persistent

def convert_response(grader, response):
	"""
	Given a grading object and a response, attempt to adapt
	the response to the type needed by the grader.
	Uses the `response_type` tagged value on the interfaces implemented
	by the grader.
	"""
	if not interfaces.IQSolution.providedBy( grader ):
		# Well, nothing to be done, no info given
		return response

	for iface in interface.providedBy( grader ).flattened():
		response_type = iface.queryTaggedValue( 'response_type' )
		if response_type:
			result = response_type( response, alternate=None ) # adapt or return if already present
			if result:
				response = result
				break

	return response

class QSolution(Persistent):
	"""
	Base class for solutions. Its :meth:`grade` method
	will attempt to transform the input based on the interfaces
	this object implements and then call the :meth:`_grade` method.
	"""

	interface.implements(interfaces.IQSolution)

	def grade( self, response ):
		return self._grade( convert_response( self, response ) )

	def _grade(self, response ):
		raise NotImplementedError(type(self), type(self).mro()) # pragma: no cover

class QMathSolution(QSolution):
	"""
	Base class for the math hierarchy.
	"""
	interface.implements(interfaces.IQMathSolution)


class _TrivialEqualityMixin(object):
	converter = unicode
	def __init__( self, value ):
		self.value = value

	def _grade( self, response):
		return self.value == self.converter(response.value)

class QNumericMathSolution(_TrivialEqualityMixin,QMathSolution):
	"""
	Numeric math solution.

	TODO: This grading mechanism is pretty poorly handled and compares
	by exact equality.
	"""

	interface.implements(interfaces.IQNumericMathSolution)
	converter = float

class QFreeResponseSolution(_TrivialEqualityMixin,QSolution):
	"""
	Simple free-response solution.
	"""
	interface.implements(interfaces.IQFreeResponseSolution)
