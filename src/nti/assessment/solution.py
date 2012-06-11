#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.assessment import interfaces
from nti.assessment import parts

from persistent import Persistent

@interface.implementer(interfaces.IQSolution)
class QSolution(Persistent):
	"""
	Base class for solutions. Its :meth:`grade` method
	will attempt to transform the input based on the interfaces
	this object implements and then call the :meth:`_grade` method.
	"""

	_part_type = parts.QPart

	def grade( self, response ):
		"""
		Convenience method for grading solutions that can be graded independent
		of their question parts.
		"""
		return self._part_type( solutions=(self,) ).grade( response )

@interface.implementer(interfaces.IQMathSolution)
class QMathSolution(QSolution):
	"""
	Base class for the math hierarchy.
	"""

class _TrivialValuedMixin(object):
	def __init__( self, value ):
		self.value = value

@interface.implementer(interfaces.IQNumericMathSolution)
class QNumericMathSolution(_TrivialValuedMixin,QMathSolution):
	"""
	Numeric math solution.

	TODO: This grading mechanism is pretty poorly handled and compares
	by exact equality.
	"""

	_part_type = parts.QNumericMathPart

@interface.implementer(interfaces.IQFreeResponseSolution)
class QFreeResponseSolution(_TrivialValuedMixin,QSolution):
	"""
	Simple free-response solution.
	"""

	_part_type = parts.QFreeResponsePart


@interface.implementer(interfaces.IQSymbolicMathSolution)
class QSymbolicMathSolution(QMathSolution):
	"""
	Symbolic math grading is redirected through
	grading components for extensibility.
	"""

	_part_type = parts.QSymbolicMathPart

@interface.implementer(interfaces.IQLatexSymbolicMathSolution)
class QLatexSymbolicMathSolution(_TrivialValuedMixin,QSymbolicMathSolution):
	"""
	The answer is defined to be in latex.
	"""

	 # TODO: Verification of the value? Minor transforms like adding $$?

@interface.implementer(interfaces.IQMatchingSolution)
class QMatchingSolution(_TrivialValuedMixin,QSolution):
	pass

@interface.implementer(interfaces.IQMultipleChoiceSolution)
class QMultipleChoiceSolution(_TrivialValuedMixin,QSolution):

	_part_type = parts.QMultipleChoicePart
