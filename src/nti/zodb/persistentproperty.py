#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes for making :class:`property` objects (actually, general descriptors)
more convenient for working with in :class:`persistent.Persistent` objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from persistent import Persistent

class PropertyHoldingPersistent(object):
	"""
	Base class mixin for a property that, when installed in a
	:class:`PersistentPropertyHolder`, can be used to hold another persistent
	object. This property object takes all responsibility for changing
	persistent state (of the instance it is installed in) if needed.
	"""

def _get_or_make_cache(cls):
	cache = getattr(cls, '_v_persistentpropertyholder_cache', None)
	if cache is None:
		cache = {}
		# Walk through the inheritance tree, *from the root down*, collecting
		# descriptors. Order matters.
		for _cls in reversed(cls.mro()):
			for k, v in _cls.__dict__.items():
				if isinstance( v, PropertyHoldingPersistent ):
					cache[k] = v
		setattr( cls, '_v_persistentpropertyholder_cache', cache )
	return cache

class PersistentPropertyHolder(Persistent):
	"""
	Lets you assign to a property without necessarily changing the
	_p_status of this object.

	In a subclass of :class:`persistent.Persistent`, the ``__setattr__``
	method sets ``_p_changed`` to True when called with a ``name`` argument
	that does not start with ``_p_`` (properties of the persistent object itself)
	or ``_v_`` (volatile properties). This makes it hard to use with conflict-reducing
	objects like :class:`nti.zodb.minmax.NumericMaximum`: instead of
	being able to define a descriptor to access and mutate them directly, you must
	remember to go through their API, and replacing existing simple attributes (a plain
	number) with a property doesn't actually reduce conflicts until all callers have
	been updated to use the API.

	This superclass fixes that problem. When :meth:`__setattr__` is called,
	it checks to see if the underlying attribute is actually a descriptor extending
	:class:`PropertyHoldingPersistent`, and if so, delegates directly to that
	object. That object is responsible for managing the persistent state of that instance.

	.. note::
		When you subclass this, you should not modify the type after the first
		instance is constructed by adding new :class:`PropertyHoldingPersistent` instances.
		As an implementation note, the ``__new__`` method caches the properties that
		are ``PropertyHoldingPersistent``. Adding new ones will bypass the cache (and make
		the instance modified) but otherwise still behave correctly. Replacing one with a
		different type of property or deleting the property altogether may not function
		correctly.

	"""

	def __new__( cls, *args, **kwargs ):
		# We do this is __new__ and avoid a metaclass so that subclasses can
		# still choose their own metaclass.
		# Sadly, some extension classes (notably Acquisition.Implicit)
		# do not call super.__new__, so we cannat count on this being done here.
		_get_or_make_cache( cls )
		return super(PersistentPropertyHolder,cls).__new__( cls, *args, **kwargs )

	def __setattr__( self, name, value ):
		descriptor = _get_or_make_cache( type(self) ).get( name )
		if descriptor is not None:
			descriptor.__set__( self, value )
		else:
			super(PersistentPropertyHolder,self).__setattr__( name, value )
