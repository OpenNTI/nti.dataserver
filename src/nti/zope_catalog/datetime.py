#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support efficiently storing datetime values in an index, normalized.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.zodb.containers import time_to_64bit_int
from persistent import Persistent

from pytz import UTC
from datetime import datetime
import time

from zc.catalog.index import DateTimeNormalizer

from nti.utils.property import CachedProperty

class TimestampTo64BitIntNormalizer(object):
	"""
	Normalizes incoming floating point objects representing Unix
	timestamps to 64-bit integers. Use this with a
	:class:`zc.catalog.catalogindex.NormalizationWrapper`
	"""
	__slots__ = ()

	def value(self, value):
		return time_to_64bit_int(value)

	# The provided date-time normalizer supports taking
	# datetime.date objects for the various range queries
	# and turning those into sequences. For example, if you ask
	# for 'any' on July 4, you get a normalized query that is all
	# datetime values in the index from July 0, 00:00 to July 4 23:59.
	# We could do that to, if we need to, but for the moment we don't care
	# because we don't do these kind of searches with this index...?
	# We don't implement those methods so that if we try to query,
	# we fail loudly


class TimestampNormalizer(Persistent):
	"""
	Normalizes incoming Unix timestamps to have a set
	resolution, by default minutes.
	"""

	# These values wind up corresponding to the
	# indices in the timetuple

	RES_DAY = 0
	RES_HOUR = 1
	RES_MINUTE = 2
	RES_SECOND = 3
	RES_MICROSECOND = 4

	def __init__(self, resolution=RES_MINUTE):
		self.resolution = resolution

	@CachedProperty('resolution')
	def _datetime_normalizer(self):
		return DateTimeNormalizer(self.resolution)

	def value(self, value):
		dt = datetime.fromtimestamp(value)
		dt = dt.replace(tzinfo=UTC)
		dt = self._datetime_normalizer.value(dt)
		return time.mktime(dt.timetuple())


class TimestampToNormalized64BitIntNormalizer(Persistent):
	"""
	Normalizes incoming Unix timestamps to have a set resolution,
	by default minutes, and then converts them to integers
	that can be stored in an :class:`nti.zodb_catalog.field.IntegerAttributeIndex`.
	"""

	def __init__(self, resolution=TimestampNormalizer.RES_MINUTE):
		self.resolution = resolution

	@CachedProperty('resolution')
	def _timestamp_normalizer(self):
		return TimestampNormalizer(self.resolution)

	@CachedProperty
	def _int_normalizer(self):
		return TimestampTo64BitIntNormalizer()

	def value(self, value):
		return self._int_normalizer.value(
			self._timestamp_normalizer.value(value))
