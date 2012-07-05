#!/usr/bin/env python
"""
Conflict resolving value/counter implementations

$Id$
"""
from __future__ import print_function, unicode_literals

import functools

from zope.minmax._minmax import Maximum, Minimum, AbstractValue

# The Default Max/Min classes exist because, in some circumstances
# during database creation a plain Maximum/Minimum loses
# its `value`: __getstate__ raises AttributeError because self.value
# is not there (for no clear reason!). These classes define it as a default

@functools.total_ordering
class AbstractNumericValue(AbstractValue):
	"""
	A numeric value that provides ordering operations.
	Defaults to zero.
	"""
	value = 0

	def __init__( self, value=0 ):
		super(AbstractNumericValue,self).__init__( value )

	def set(self,value):
		self.value = value

	def __eq__( self, other ):
		try:
			return other is self or self.value == other.value
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __hash__(self):
		return self.value

	def __lt__(self, other ):
		try:
			return self.value < other.value
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __gt__(self,other):
		try:
			return self.value > other.value
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __str__( self ):
		return str(self.value)

	def __repr__( self ):
		return "%s(%s)" %(self.__class__.__name__, self.value)

class _ConstantZeroValue(AbstractNumericValue):
	"""
	Use this as a class attribute for a default values of zero. The
	value cannot be changed, and instances cannot be serialized.
	"""

	def __init__( self, value=0 ):
		super(_ConstantZeroValue,self).__init__( value=0 )
		assert 'value' not in self.__dict__

	def __getstate__( self ): raise TypeError()
	def _p_resolveConflict(self, old, committed, new): raise NotImplementedError()

	value = property( lambda s: 0, lambda s, nv: None )

_czv = _ConstantZeroValue()

def ConstantZeroValue():
	return _czv
ConstantZeroValue.__doc__ = _ConstantZeroValue.__doc__

class NumericMaximum(AbstractNumericValue,Maximum):
	"""
	Maximizes the number during conflicts.
	"""


class NumericMinimum(AbstractNumericValue,Minimum):
	"""
	Minimizes the number during conflicts.
	"""


class MergingCounter(AbstractNumericValue):
	"""
	A :mod:`zope.minmax` item that resolves conflicts by
	merging the numeric value of the difference in magnitude of changes.
	Intented to be used for monotonically increasing counters.
	"""

	def increment(self):
		self.value += 1

	def _p_resolveConflict( self, oldState, savedState, newState ):
		saveDiff = savedState - oldState
		newDiff = newState - oldState
		savedState = oldState + saveDiff + newDiff
		return savedState
