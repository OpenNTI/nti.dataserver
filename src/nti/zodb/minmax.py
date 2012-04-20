#!/usr/bin/env python
"""
Conflict resolving value/counter implementatinos
$Revision$
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
		return other is self or (isinstance(other,AbstractNumericValue) and self.value == other.value)

	def __hash__(self):
		return self.value

	def __lt__(self, other ):
		return self.value < other.value

	def __gt__(self,other):
		return self.value > other.value

	def __str__( self ):
		return str(self.value)

	def __repr__( self ):
		return "%s(%s)" %(self.__class__.__name__, self.value)

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
	A :module:`zope.minmax` item that resolves conflicts by
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
