#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces for objects defined in the ZODB package.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import schema
from zope.minmax import interfaces as minmax_interfaces

class ITokenBucket(interface.Interface):
	"""
	A token bucket is used in rate limiting applications.
	It has a maximum capacity and a rate at which tokens are regenerated
	(typically this is in terms of absolute time).

	Clients attempt to consume tokens and are either allowed
	or denied based on whether there are enough tokens in the bucket.
	"""

	fill_rate = schema.Float( title="The rate in tokens per second at which new tokens arrive.",
							  min=0.0)
	capacity = schema.Float( title="The maximum capacity of the token bucket.",
							 min=0.0)

	tokens = schema.Float( title="The current number of tokens in the bucket at this instant.",
						   min=0.0 )

	def consume(tokens=1):
		"""
		Consume tokens from the bucket.

		:return: True if there were sufficient tokens, otherwise False.
			If True, then the value of `tokens` will have been reduced.
		"""

class INumericValue(minmax_interfaces.IAbstractValue):
	"""
	A persistent numeric value with conflict resolution.
	"""
	value = schema.Float( title="The numeric value of this object." )

	def set(value):
		"""Change the value of this object to the given value."""

	def __eq__( other ):
		"""Is this object holding a value numerically equal to the other?"""

	def __hash__():
		"""This object hashes like its value."""

	def __lt__( other ):
		"""These objects are ordered like their values."""

	def __gt__(other):
		"""These values are ordered like their values."""

class INumericCounter(INumericValue):
	"""
	A counter that can be incremented. Conflicts are resolved by
	merging the numeric value of the difference in magnitude of changes.
	Intented to be used for monotonically increasing counters.
	"""
