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

# Give all these things a 'set' method, a point for subclasses
# to potentially override
def _set(self, value):
	self.value = value
assert 'set' not in AbstractValue.__dict__ or AbstractValue.set is _set # catch incompatible changes
AbstractValue.set = _set

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

	def set( self, value ):
		pass

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

		def __init__( self, name, holder, prop ):
			_ConstantZeroValue.__init__( self )
			self.__name__ = name
			self.holder = holder
			self.prop = prop

		def increment(self, amount=1):
			# Use the original NumericPropertyDefaultingToZero descriptor
			# to set the value, calling the factory and storing it.
			self.prop.__set__( self.holder, amount )
			return self.prop.__get__( self.holder, type(self.holder) )

		def set( self, value ):
			if value == 0:
				return
			self.prop.__set__( self.holder, value )


	as_number = False
	def __init__( self, name, factory, as_number=False ):
		"""
		Creates a new property in a new-style class that does not use ``__slots__``
		(persistent classes shouldn't use ``__slots__`` anyway).

		:param name: The name of the property; this will be the key in the instance
			dictionary. This should match the name of the property
			(e.g., ``a = NumericPropertyDefaultingToZero( 'a',...)``) but is not required
			to.
		"""
		self.__name__ = name
		self.factory = factory
		if as_number:
			self.as_number = True

	def __activate( self, inst ):
		"we must activate objects before accessing their dict otherwise it may not be loaded"
		try:
			inst._p_activate()
		except AttributeError:
			pass

	def __get__( self, inst, klass ):
		if inst is None:
			return klass

		self.__activate( inst )
		if self.__name__ in inst.__dict__:
			value = inst.__dict__[self.__name__]
			return value.value if self.as_number else value

		return 0 if self.as_number else  self.IncrementingZeroValue( self.__name__, inst, self )

	def __set__( self, inst, value ):
		self.__activate( inst )
		val = inst.__dict__.get( self.__name__, None )
		if val is None:
			if value == 0:
				return # not in dict, but they gave us the default value, so ignore it
			val = self.factory( value )
			inst.__dict__[self.__name__] = val
			inst._p_changed = True
			if getattr(inst, '_p_jar', None) is not None:
				inst._p_jar.add( val )
		else:
			val.set( value )

	def __delete__( self, inst ):
		self.__activate( inst )
		if self.__name__ in inst.__dict__:
			del inst.__dict__[self.__name__]
			inst._p_changed = True
