#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import contains_inanyorder

import unittest

from nti.zodb.minmax import MergingCounter
from nti.zodb.minmax import NumericMaximum
from nti.zodb.minmax import NumericMinimum
from nti.zodb.minmax import NumericPropertyDefaultingToZero

from nti.zodb.persistentproperty import PersistentPropertyHolder

class TestPersistentProperty(unittest.TestCase):
	
	def test_that_if_superclass_created_first_subclass_cache_is_correct(self):
		
		class BaseWithProperty(PersistentPropertyHolder):
			a = NumericPropertyDefaultingToZero( b'a', NumericMaximum, as_number=True )
			b = NumericPropertyDefaultingToZero( b'b', MergingCounter )
	
		class DerivedWithProperty(BaseWithProperty):
			c = NumericPropertyDefaultingToZero( b'c', NumericMinimum )
	
		base = BaseWithProperty()
		assert_that( base._v_persistentpropertyholder_cache.keys(),
					 contains_inanyorder('a', 'b') )
	
		derived = DerivedWithProperty()
		assert_that( derived._v_persistentpropertyholder_cache.keys(),
					 contains_inanyorder('a', 'b', 'c'))
