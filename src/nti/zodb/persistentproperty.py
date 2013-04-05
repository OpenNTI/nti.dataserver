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

	"""

	def __setattr__( self, name, value ):
		# Check to see if we have something that takes responsibility.
		# NOTE: This could be cached if benchmarks show it to be helpful.
		# Most benefit would be to cache it on the type.
		# This assumes that the type isn't modified later.
		# Easiest would be to do that in __new__; avoid a metaclass
		# because subclasses might want their own metaclass.
		descriptor = getattr( type(self), name, None )
		if isinstance( descriptor, PropertyHoldingPersistent ):
			descriptor.__set__( self, value )
		else:
			super(PersistentPropertyHolder,self).__setattr__( name, value )
