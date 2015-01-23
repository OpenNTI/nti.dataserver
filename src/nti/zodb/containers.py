#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions relating to working with ZODB-level containers, the BTrees package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import struct

# ! means network byte order, in case we cross architectures
# anywhere (doesn't matter), but also causes the sizes to be
# standard, which may matter between 32 and 64 bit machines
# q is 64-bit long int, d is 64-bit double

_float_to_double_bits = struct.Struct(b'!d').pack
_double_bits_to_long = struct.Struct(b'!q').unpack

_long_to_double_bits = struct.Struct(b'!q').pack
_double_bits_to_float = struct.Struct(b'!d').unpack

def time_to_64bit_int( value ):
	"""
	Given a Python floating point object (usually a time value),
	return a 64-bit long int that represents it. Useful for
	storing as the value in a OL tree, when you really want a float
	(since BTrees does not provide OF), or as a key in a Lx tree.
	"""
	# Note that to handle negative values we must be signed,
	# otherwise we get ValueError from the btree
	if value is None: # pragma: no cover
		raise ValueError("For consistency, you must supply the lastModified value" )

	return _double_bits_to_long( _float_to_double_bits( value ) )[0]

ZERO_64BIT_INT = time_to_64bit_int( 0.0 )

def bit64_int_to_time( value ):
	return _double_bits_to_float( _long_to_double_bits(value) )[0]


assert bit64_int_to_time(ZERO_64BIT_INT) == 0.0
