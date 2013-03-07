#!/usr/bin/env python
"""
Conflict resolving value/counter implementations

$Id$
"""
from __future__ import print_function, unicode_literals

import functools

from . import interfaces
from zope import interface
from zope.minmax._minmax import Maximum, Minimum, AbstractValue

# The Default Max/Min classes exist because, in some circumstances
# during database creation a plain Maximum/Minimum loses
# its `value`: __getstate__ raises AttributeError because self.value
# is not there (for no clear reason!). These classes define it as a default

@functools.total_ordering
@interface.implementer(interfaces.INumericValue)
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

	# Comparison methods
	def __eq__( self, other ):
		try:
			return other is self or self.value == other.value
		except AttributeError: # pragma: no cover
			return NotImplemented

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

	def __hash__(self):
		return self.value

	# Numeric methods
	def __isub__(self, other):
		other_value = getattr( other, 'value', other )
		self.set( self.value - other_value )
		return self

	def __iadd__(self, other):
		other_value = getattr( other, 'value', other )
		self.set( self.value + other_value )
		return self

	def __rsub__( self, other ):
		# other - self.
		# By definition, not called if other is the same type as this
		return other - self.value

	def __add__( self, other ):
		other_value = getattr( other, 'value', other )
		result = self.value + other_value
		if other_value is not other:
			result = type(self)(result)
		return result

	def __str__( self ):
		return str(self.value)

	def __repr__( self ):
		return "%s(%s)" % (self.__class__.__name__, self.value)

class _ConstantZeroValue(AbstractNumericValue):
	"""
	Use this as a class attribute for a default values of zero. The
	value cannot be changed, and instances cannot be serialized.
	"""

	def __init__( self, value=0 ):
		super(_ConstantZeroValue,self).__init__( value=0 )
		assert 'value' not in self.__dict__

	def __getstate__( self ):
		raise TypeError()

	def _p_resolveConflict(self, old, committed, new):
		raise NotImplementedError()

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

@interface.implementer(interfaces.INumericCounter)
class MergingCounter(AbstractNumericValue):
	"""
	A :mod:`zope.minmax` item that resolves conflicts by
	merging the numeric value of the difference in magnitude of changes.
	Intented to be used for monotonically increasing counters.
	"""

	def increment(self, amount=1):
		assert amount >= 0
		self.value += amount
		return self

	def _p_resolveConflict( self, oldState, savedState, newState ):
		saveDiff = savedState - oldState
		newDiff = newState - oldState
		savedState = oldState + saveDiff + newDiff
		return savedState

from .persistentproperty import PropertyHoldingPersistent

class NumericPropertyDefaultingToZero(PropertyHoldingPersistent):
	"""
	In persistent objects (that extend :class:`nti.zodb.persistentproperty.PersistentPropertyHolder`),
	use this to hold a merging counter or numeric minimum or maximum.
	"""

	@interface.implementer(interfaces.INumericCounter)
	class IncrementingZeroValue(_ConstantZeroValue):

		def __init__( self, name, holder ):
			_ConstantZeroValue.__init__( self )
			self.__name__ = name
			self.holder = holder

		def increment(self, amount=1):
			setattr( self.holder, self.__name__, amount )
			return getattr( self.holder, self.__name__ )

		def set( self, value ):
			if value == 0:
				return
			setattr( self.holder, self.__name__, value )


	as_number = False
	def __init__( self, name, factory, as_number=False ):
		"""
		Creates a new property.

		:param name: The name of the property; this will be the key in the instance
			dictionary.
		"""
		self.__name__ = name
		self.factory = factory
		if as_number:
			self.as_number = True

	def __get__( self, inst, klass ):
		if inst is None:
			return klass

		if self.__name__ in inst.__dict__:
			value = inst.__dict__[self.__name__]
			return value.value if self.as_number else value

		return 0 if self.as_number else  self.IncrementingZeroValue( self.__name__, inst )

	def __set__( self, inst, value ):
		val = inst.__dict__.get( self.__name__, None )
		if val is None:
			if value == 0:
				return # not in dict, but they gave us the default value, so ignore it
			val = self.factory( value )
			inst.__dict__[self.__name__] = val
			inst._p_changed = True
			if inst._p_jar:
				inst._p_jar.add( val )
		else:
			val.set( value )

	def __delete__( self, inst ):
		if self.__name__ in inst.__dict__:
			del inst.__dict__[self.__name__]
			inst._p_changed = True
