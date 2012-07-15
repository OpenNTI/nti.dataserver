#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_

from zope import interface
from zope.location import interfaces as loc_interfaces

from nti.dataserver import traversal
import nti.tests

setUpModule = lambda: nti.tests.module_setup( set_up_packages=(nti.dataserver,) )
tearDownModule = nti.tests.module_teardown


def test_unicode_resource_path():

	@interface.implementer(loc_interfaces.IRoot)
	class Root(object):
		__parent__ = None
		__name__ = None


	@interface.implementer(loc_interfaces.ILocation)
	class Middle(object):
		__parent__ = Root()
		__name__ = u'Middle'

	@interface.implementer(loc_interfaces.ILocation)
	class Leaf(object):
		__parent__ = Middle()
		__name__ = u'\u2019'

	assert_that( traversal.resource_path( Leaf() ),
				 is_( '/Middle/%E2%80%99' ) )
