#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import greater_than
from hamcrest import has_entry


import BTrees
import struct

from ..containers import time_to_64bit_int


class TestTimes(unittest.TestCase):

	def test_negative_values_in_btree(self):
		bt = BTrees.family64.IO.BTree()

		for i in xrange(-1, -10000, -5):
			bt[time_to_64bit_int(i)] = str(i)


		for i in xrange(-1, -10000, -5):
			assert_that( bt, has_entry( time_to_64bit_int(i), str(i)))


	def test_positive_values_in_btree(self):
		bt = BTrees.family64.IO.BTree()

		for i in xrange(1, 10000, 10):
			bt[time_to_64bit_int(i)] = str(i)


		for i in xrange(1, 10000, 10):
			assert_that( bt, has_entry( time_to_64bit_int(i), str(i)))

	def test_increasing(self):

		prev = 0
		i = 1
		while i < 10000:

			ti = time_to_64bit_int(i)
			nti = time_to_64bit_int(-i)

			assert_that( ti, greater_than( time_to_64bit_int(prev)))
			assert_that( ti, greater_than( nti ))

			prev = i
			i += 1.5

	def test_legacy_unsigned_pack_equivalent(self):
		# We used to pack with Q, now we pack with q.
		# Q was invalid for negative numbers, but we need to be
		# sure that q unpacks everything the same as it used to


		for i in xrange(1, 10000, 5):

			ti = struct.pack(b'!q', i)
			qti = struct.pack(b'!Q', i)

			assert_that( ti, is_(qti))

			uti = struct.unpack(b'!q', ti)[0]
			uqti = struct.unpack(b'!Q', qti)[0]

			assert_that( uti, is_(i))
			assert_that( uti, is_(uqti) )

			assert_that( struct.unpack(b'!q', qti)[0],
						 is_(i))
