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
from nti.utils._compat import sleep

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
		:keyword fill_rate: The rate in fractional tokens per second that
			the bucket will fill. The default is to add one
			token per second.
		"""
		self.capacity = float(capacity)
		self.fill_rate = float(fill_rate)

		# Conflict resolution: the tokens in the bucket is always
		# taken as the smallest. Time, of course, marches ever upwards
		# TODO: This could probably be better
		self._tokens = minmax.NumericMinimum( self.capacity )
		self._timestamp = minmax.NumericMaximum( time() )

	def consume(self, tokens=1):
		"""Consume one or more tokens from the bucket. Returns True if there were
		sufficient tokens otherwise False."""
		if tokens <= self.tokens:
			self._tokens -= tokens
			return True

		return False

	def wait_for_token(self):
		"""
		Consume a single token from the bucket, blocking until one is available
		if need be.
		"""

		while not self.consume():
			needed_token_count = 1.0 - self._tokens.value
			# How long will it take to get that token?
			how_long = needed_token_count * self.fill_rate
			sleep( how_long )
		return True

	@property
	def tokens(self):
		"""The fractional number of tokens currently in the bucket."""
		now = time()
		if self._tokens.value < self.capacity:
			delta = self.fill_rate * (now - self._timestamp)
			self._tokens.set( min(self.capacity, self._tokens + delta) )
		self._timestamp.set( now )
		return self._tokens.value

	def __repr__(self):
		return "%s(%s,%s)" % (type(self).__name__, self.capacity, self.fill_rate)
