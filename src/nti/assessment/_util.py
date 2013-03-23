#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

_marker = object()

class TrivialValuedMixin(object):
	value = None

	def __init__( self, *args, **kwargs ):
		# The contents of ``self.value`` come from either the first arg (if positional args are given) or the kwarg named
		# such.

		if args:
			value = args[0]
		elif 'value' in kwargs:
			value = kwargs.get( 'value' )
		else:
			value = None

		# Avoid the appearance of trying to pass args to object.__init__ to avoid a Py3K warning
		init = super(TrivialValuedMixin,self).__init__
		if getattr( init, '__objclass__', None) is not object: # object's init is a method-wrapper
			init( *args, **kwargs )

		if value is not None:
			self.value = value

	def __eq__( self, other ):
		try:
			return self is other or self.value == other.value
		except AttributeError:
			return NotImplemented

	def __ne__( self, other ):
		try:
			return self is not other and self.value != other.value
		except AttributeError: #pragma: no cover
			return NotImplemented

	def __hash__( self ):
		return superhash( self.value )

	def __str__( self ):
		return str( self.value )

	def __repr__( self ):
		return "%s.%s(%r)" % (self.__class__.__module__, self.__class__.__name__, self.value )

def superhash( value ):
	try:
		return hash(value)
	except TypeError:
		# Dict
		xhash = 4201029
		try:
			# Sort these, they have no order
			for item in sorted( value.items() ):
				xhash ^= superhash(item)
			return xhash
		except AttributeError:
			# Iterable which must be unsorted
			for item in value:
				xhash ^= superhash( item )
			return xhash
