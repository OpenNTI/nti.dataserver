#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions relating to working with ZODB-level containers, the BTrees package.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)



import struct
def time_to_64bit_int( value ):
	"""
	Given a Python floating point object (usually a time value), return a 64-bit unsigned int that represents it.
	Useful for storing in a OI tree, when you really want a float (since BTrees
	does not provide OF).
	"""
	if value is None: # pragma: no cover
		raise ValueError("For consistency, you must supply the lastModified value" )
	# ! means network byte order, in case we cross architectures
	# anywhere (doesn't matter), but also causes the sizes to be
	# standard, which may matter between 32 and 64 bit machines
	# Q is 64-bit unsigned int, d is 64-bit double
	return struct.unpack( b'!Q', struct.pack( b'!d', value ) )[0]

ZERO_64BIT_INT = time_to_64bit_int( 0.0 )

def bit64_int_to_time( value ):
	return struct.unpack( b'!d', struct.pack( b'!Q', value ) )[0]
