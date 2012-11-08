#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of the token bucket algorithm.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from . import interfaces
from . import minmax

from time import time


@interface.implementer(interfaces.ITokenBucket)
class PersistentTokenBucket(object):
	"""
	Persistent implementation of the token bucket algorithm.
	If the ZODB is used from multiple machines, relies on their
	clocks being relatively synchronized to be effective.

	Initially based on `an ActiveState recipe <http://code.activestate.com/recipes/511490-implementation-of-the-token-bucket-algorithm/>`_
	"""

	def __init__(self, capacity, fill_rate=1.0):
		"""
		Creates a new token bucket, initially full.

		:param capacity: The max number of tokens in the bucket (also
			the initial number of tokens in the bucket.
		:keyword fill_rate: The rate in tokens per second that
			the bucket will fill.
		"""
		self.capacity = float(capacity)
		self.fill_rate = float(fill_rate)

		# Conflict resolution: the tokens in the bucket is always
		# taken as the smallest. Time, of course, marches ever upwards
		# TODO: This could probably be better
		self._tokens = minmax.NumericMinimum( capacity )
		self._timestamp = minmax.NumericMaximum( time() )

	def consume(self, tokens=1):
		"""Consume tokens from the bucket. Returns True if there were
		sufficient tokens otherwise False."""
		if tokens <= self.tokens:
			self._tokens -= tokens
		else:
			return False
		return True

	@property
	def tokens(self):
		now = time()
		if self._tokens.value < self.capacity:
			delta = self.fill_rate * (now - self._timestamp)
			self._tokens.set( min(self.capacity, self._tokens + delta) )
		self._timestamp.set( now )
		return self._tokens.value

	def __repr__(self):
		return "%s(%s,%s)" % (type(self).__name__, self.capacity, self.fill_rate)
