#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import

from zope import interface

from persistent import Persistent
from nti.externalization.externalization import make_repr

from nti.assessment import parts
from nti.assessment import interfaces
from nti.assessment._util import TrivialValuedMixin as _TrivialValuedMixin
from nti.assessment._util import superhash

@interface.implementer(interfaces.IQSolution)
class QSolution(Persistent):
	"""
	Base class for solutions. Its :meth:`grade` method
	will attempt to transform the input based on the interfaces
	this object implements and then call the :meth:`.QPart.grade` method.
	"""

	#: Defines the factory used by the :meth:`grade` method to construct
	#: a :class:`.IQPart` object. Also, instances are only equal if this value
	#: is equal
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

	allowed_units = None # No defined unit handling

	def __init__( self, *args, **kwargs ):
		super(QMathSolution,self).__init__()
		allowed_units = args[1] if len(args) > 1 else kwargs.get( 'allowed_units' )
		if allowed_units is not None:
			self.allowed_units = allowed_units # TODO: Do we need to defensively copy?

def _eq_(self, other):
	try:
		return other is self or (self._part_type == other._part_type
								 and self.weight == other.weight
								 and self.value == other.value)
	except AttributeError: #pragma: no cover
		return NotImplemented

def _ne_(self, other):
	return not (self == other) is True

def __hash__(self):
	return hash(self.weight) + superhash(self.value)

@interface.implementer(interfaces.IQNumericMathSolution)
class QNumericMathSolution(_TrivialValuedMixin,QMathSolution):
	"""
	Numeric math solution.

	.. todo:: This grading mechanism is pretty poorly handled and compares
		by exact equality.
	"""

	_part_type = parts.QNumericMathPart

	__eq__ = _eq_
	__ne__ = _ne_
	__hash__ = __hash__

@interface.implementer(interfaces.IQFreeResponseSolution)
class QFreeResponseSolution(_TrivialValuedMixin,QSolution):
	"""
	Simple free-response solution.
	"""

	_part_type = parts.QFreeResponsePart

	__eq__ = _eq_
	__ne__ = _ne_
	__hash__ = __hash__

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
	__hash__ = __hash__

@interface.implementer(interfaces.IQMatchingSolution)
class QMatchingSolution(_TrivialValuedMixin,QSolution):

	_part_type = parts.QMatchingPart

	__eq__ = _eq_
	__ne__ = _ne_
	__hash__ = __hash__

@interface.implementer(interfaces.IQMultipleChoiceSolution)
class QMultipleChoiceSolution(_TrivialValuedMixin,QSolution):

	_part_type = parts.QMultipleChoicePart

	__eq__ = _eq_
	__ne__ = _ne_
	__hash__ = __hash__

@interface.implementer(interfaces.IQMultipleChoiceMultipleAnswerSolution)
class QMultipleChoiceMultipleAnswerSolution(_TrivialValuedMixin,QSolution):
	"""
	The answer is defined as a list of selections which best represent
	the correct answer.
	"""

	_part_type = parts.QMultipleChoiceMultipleAnswerPart

	__eq__ = _eq_
	__ne__ = _ne_
	__hash__ = __hash__
