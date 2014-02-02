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


from hamcrest import assert_that

from hamcrest import contains_inanyorder

from nti.zodb.persistentproperty import PersistentPropertyHolder
from nti.zodb.minmax import MergingCounter, NumericMinimum, NumericMaximum, NumericPropertyDefaultingToZero


def test_that_if_superclass_created_first_subclass_cache_is_correct():
	class BaseWithProperty(PersistentPropertyHolder):

		a = NumericPropertyDefaultingToZero( 'a', NumericMaximum, as_number=True )
		b = NumericPropertyDefaultingToZero( 'b', MergingCounter )

	class DerivedWithProperty(BaseWithProperty):

		c = NumericPropertyDefaultingToZero( 'c', NumericMinimum )

	base = BaseWithProperty()
	assert_that( base._v_persistentpropertyholder_cache.keys(),
				 contains_inanyorder('a', 'b') )

	derived = DerivedWithProperty()
	assert_that( derived._v_persistentpropertyholder_cache.keys(),
				 contains_inanyorder('a', 'b', 'c'))
