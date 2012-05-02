#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.assessment import interfaces
from nti.assessment import parts

from persistent import Persistent


class QSolution(Persistent):
	"""
	Base class for solutions. Its :meth:`grade` method
	will attempt to transform the input based on the interfaces
	this object implements and then call the :meth:`_grade` method.
	"""

	interface.implements(interfaces.IQSolution)

	_part_type = parts.QPart

	def grade( self, response ):
		"""
		Convenience method for grading solutions that can be graded independent
		of their question parts.
		"""
		return self._part_type( solutions=(self,) ).grade( response )

class QMathSolution(QSolution):
	"""
	Base class for the math hierarchy.
	"""
	interface.implements(interfaces.IQMathSolution)


class _TrivialValuedMixin(object):
	def __init__( self, value ):
		self.value = value


class QNumericMathSolution(_TrivialValuedMixin,QMathSolution):
	"""
	Numeric math solution.

	TODO: This grading mechanism is pretty poorly handled and compares
	by exact equality.
	"""

	interface.implements(interfaces.IQNumericMathSolution)


class QFreeResponseSolution(_TrivialValuedMixin,QSolution):
	"""
	Simple free-response solution.
	"""
	interface.implements(interfaces.IQFreeResponseSolution)


class QSymbolicMathSolution(QMathSolution):
	"""
	Symbolic math grading is redirected through
	grading components for extensibility.
	"""
	interface.implements(interfaces.IQSymbolicMathSolution)
	_part_type = parts.QSymbolicMathPart

class QLatexSymbolicMathSolution(_TrivialValuedMixin,QSymbolicMathSolution):
	"""
	The answer is defined to be in latex.
	"""

	interface.implements(interfaces.IQLatexSymbolicMathSolution)



	 # TODO: Verification of the value? Minor transforms like adding $$?

class QMultipleChoiceSolution(_TrivialValuedMixin,QSolution):
	interface.implements(interfaces.IQMultipleChoiceSolution)

	_part_type = parts.QMultipleChoicePart
