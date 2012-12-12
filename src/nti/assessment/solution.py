#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.externalization.externalization import make_repr

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

	weight = 1.0

	def grade( self, response ):
		"""
		Convenience method for grading solutions that can be graded independent
		of their question parts.
		"""
		return self._part_type( solutions=(self,) ).grade( response )

QSolution.__repr__ = make_repr()

@interface.implementer(interfaces.IQMathSolution)
class QMathSolution(QSolution):
	"""
	Base class for the math hierarchy.
	"""

from ._util import TrivialValuedMixin as _TrivialValuedMixin


def _eq_(self, other):
	try:
		return other is self or (self._part_type == other._part_type
								 and self.weight == other.weight
								 and self.value == other.value)
	except AttributeError: #pragma: no cover
		return NotImplemented

def _ne_(self, other):
	return not (self == other) is True

@interface.implementer(interfaces.IQNumericMathSolution)
class QNumericMathSolution(_TrivialValuedMixin,QMathSolution):
	"""
	Numeric math solution.

	TODO: This grading mechanism is pretty poorly handled and compares
	by exact equality.
	"""

	_part_type = parts.QNumericMathPart

	__eq__ = _eq_
	__ne__ = _ne_

@interface.implementer(interfaces.IQFreeResponseSolution)
class QFreeResponseSolution(_TrivialValuedMixin,QSolution):
	"""
	Simple free-response solution.
	"""

	_part_type = parts.QFreeResponsePart

	__eq__ = _eq_
	__ne__ = _ne_


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

	__eq__ = _eq_
	__ne__ = _ne_

@interface.implementer(interfaces.IQMatchingSolution)
class QMatchingSolution(_TrivialValuedMixin,QSolution):

	_part_type = parts.QMatchingPart

	__eq__ = _eq_
	__ne__ = _ne_

@interface.implementer(interfaces.IQMultipleChoiceSolution)
class QMultipleChoiceSolution(_TrivialValuedMixin,QSolution):

	_part_type = parts.QMultipleChoicePart

	__eq__ = _eq_
	__ne__ = _ne_

@interface.implementer(interfaces.IQMultipleChoiceMultipleAnswerSolution)
class QMultipleChoiceMultipleAnswerSolution(_TrivialValuedMixin,QSolution):
	"""
	The answer is defined as a list of selections which best represent
	the correct answer.
	"""

	_part_type = parts.QMultipleChoiceMultipleAnswerPart

	__eq__ = _eq_
	__ne__ = _ne_

