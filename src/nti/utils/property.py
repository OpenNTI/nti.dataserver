#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities having to do with property definitions and access.


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#logger = __import__('logging').getLogger(__name__)
import operator

def alias(prop_name, doc=None):
	"""
	Returns a property that is a read/write alias for another attribute
	of the object.

	See :func:`dict_alias`.
	"""
	if doc is None:
		doc = 'Alias for ' + prop_name
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
		doc = 'Read-only alias for ' + prop_name
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
		doc = 'Alias for ' + key_name
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
		doc = 'Read-only alias for ' + key_name
	return property( lambda self: self.__dict__[key_name],
					 doc=doc )
