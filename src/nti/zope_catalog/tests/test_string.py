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
from hamcrest import contains
from hamcrest import has_entry

from nti.testing import base
from nti.testing import matchers

from ..string import StringTokenNormalizer
from ..index import NormalizationWrapper

class TestStringNormalizer(unittest.TestCase):
	field = 'ABC'
	def test_value(self):
		assert_that( StringTokenNormalizer().value(b'ABC'),
					 is_('abc'))

	def test_index_search(self):
		from zc.catalog.index import ValueIndex

		index = NormalizationWrapper('field',
									 index=ValueIndex(),
									 normalizer=StringTokenNormalizer())

		index.index_doc(1, self)

		assert_that( index.values(),
					 contains('abc'))

		assert_that( index.apply( ('ABC', 'ABC')),
					 contains(1))
