#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities having to do with property definitions and access.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import operator

from zope.annotation.interfaces import IAnnotations

def alias(prop_name, doc=None):
	"""
	Returns a property that is a read/write alias for another attribute
	of the object.

	See :func:`dict_alias`.
	"""
	if doc is None:
		doc = 'Alias for :attr:`' + prop_name + '`'
	prop_name = str(prop_name) # native string
	return property( lambda self: getattr( self, prop_name ),
					 lambda self, nv: setattr( self, prop_name, nv ),
					 doc=doc )

def read_alias(prop_name, doc=None):
	"""
	Returns a property that is a read-only alias for another attribute
	of the object.

	See :func:`dict_read_alias`.
	"""
	if doc is None:
		doc = 'Read-only alias for :attr:`' + prop_name + '`'
	return property( lambda self: getattr( self, prop_name ),
					 doc=doc )

def dict_alias(key_name, doc=None):
	"""
	Returns a property that is a read/write alias for a value in the
	instance's dictionary.

	See :func:`alias` for a more general version; this is a speed or
	access optimization.
	"""
	if doc is None:
		doc = 'Alias for :attr:`' + key_name + '`'
	key_name = str(key_name) # native string
	return property( lambda self: self.__dict__[key_name],
					 lambda self, nv: operator.setitem( self.__dict__, key_name, nv),
					 doc=doc )

def dict_read_alias(key_name, doc=None):
	"""
	Returns a property that is a read-only alias for a value in the
	instances dictionary.

	See :func:`read_alias` for a more general version; this is a speed or
	access optimization.
	"""
	if doc is None:
		doc = 'Read-only alias for :attr:`' + key_name + '`'
	return property( lambda self: self.__dict__[key_name],
					 doc=doc )


def annotation_alias(annotation_name, annotation_property=None, default=None, delete=False, delete_quiet=True, doc=None):
	"""
	Returns a property that is a read/write alias for
	a value stored as a :class:`zope.annotation.interface.IAnnotations`.

	The object itself may be adaptable to an IAnnotations, or a property
	of the object may be what is adaptable to the annotation. The later is intended
	for use in adapters when the context object is what should be adapted.

	:keyword bool delete: If ``True`` (not the default), then the property can be used
		to delete the annotation.
	:keyword bool delete_quiet: If ``True`` and `delete` is also True, then the property
		will ignore key errors when deleting the annotation value.
	:keyword str annotation_property: If set to a string, it is this property
		of the object that will be adapted to IAnnotations. Most often this will
		be ``context`` when used inside an adapter.
	"""

	if doc is None:
		doc = 'Alias for annotation ' + annotation_name

	factory = IAnnotations
	if annotation_property:
		factory = lambda self: IAnnotations( getattr( self, annotation_property ) )

	fget = lambda self: factory(self).get(annotation_name, default)
	fset = lambda self, nv: operator.setitem( factory(self), annotation_name, nv )
	fdel = None
	if delete:
		def fdel(self):
			try:
				del factory(self)[annotation_name]
			except KeyError:
				if not delete_quiet:
					raise

	return property( fget, fset, fdel,
					 doc=doc )

from zope.cachedescriptors.property import readproperty
readproperty = readproperty # export
from zope.cachedescriptors.property import CachedProperty as _CachedProperty
from zope.cachedescriptors.property import Lazy as _Lazy
from functools import update_wrapper

class Lazy(_Lazy):
	"""
	Just like :class:`zope.cachedescriptors.property.Lazy`, except
	properly preserves documentation and other attributes.
	"""

	pass

# Actually, we do this by default, but encourage
# the proper importing
_Lazy_init__ = _Lazy.__init__
def _patch_Lazy_init(self,func,**kwargs):
	_Lazy_init__(self,func,**kwargs)
	update_wrapper(self,func)
_Lazy.__init__ = _patch_Lazy_init

def CachedProperty(*args):
	"""
	Just like :class:`zope.cachedescriptors.property.CachedProperty`, except
	usable directly as an annotation when given names. Any of these patterns
	will work:

	* ``@CachedProperty``
	* ``@CachedProperty()``
	* ``@CachedProperty('n','n2')``

	"""

	if not args: # @CachedProperty()
		return _CachedProperty # A callable that produces the decorated function

	arg1 = args[0]
	names = args[1:]
	if callable(arg1): # @CachedProperty
		return _CachedProperty( arg1 )

	# @CachedProperty( 'n' )
	# Ok, must be a list of string names. Which means we are used like a factory
	# so we return a callable object to produce the actual decorated function
	def factory(function):
		return _CachedProperty( function, arg1, *names )
	return factory


# Like the above, preserve docs
_CachedProperty_init__ = _CachedProperty.__init__
def _patch_CachedProperty_init(self,func,*names):
	_CachedProperty_init__(self, func, *names)
	update_wrapper(self,func)
_CachedProperty.__init__ = _patch_CachedProperty_init

class LazyOnClass(object):
	"""
	Like :class:`zope.cachedescriptors.property.Lazy`, but
	when it caches, it caches on the class itself, not the instance,
	thus sharing the value. Thus, the value should be immutable and
	independent of any other state.
	"""

	def __init__( self, func ):
		self._func = func
		self.klass_cache_name = '_v__LazyOnClass_' + self._func.__name__

	def __get__( self, inst, klass ):
		if inst is None:
			return self

		# In order to let this be resetable, to keep access
		# to this object and the original function, we
		# use a different name
		klass_cache_name = self.klass_cache_name
		val = getattr( klass, klass_cache_name, self )
		if val is self:
			val = self._func(inst)
			setattr( klass, klass_cache_name, val )
		return val
