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
from hamcrest import is_not as does_not
from hamcrest import has_key
from hamcrest import has_property

from nti.testing import base
from nti.testing import matchers

import cPickle

from ..bucket import AbstractKey



class TestBucketPickle(unittest.TestCase):

	def test_no_volatile_attrs(self):
		key = AbstractKey()
		key._v_test = 1
		key.a = 42

		s = cPickle.dumps(key)

		key2 = cPickle.loads(s)

		assert_that( key2.__dict__,
					 does_not( has_key('_v_test' )) )
		assert_that( key2, has_property('a', 42))

		key2.__setstate__( {'_v_test': 1} )

		assert_that( key2.__dict__,
					 does_not( has_key('_v_test' )) )
