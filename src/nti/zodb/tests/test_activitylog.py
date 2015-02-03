#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import has_property

from nti.zodb.activitylog import _AbstractActivityMonitor as ActivityMonitor

def test_base():
	
	class Base(object):
		pass

	base = Base()
	base.b = 1
	mon = ActivityMonitor( base )

	assert_that( mon, has_property( 'b', 1 ) )
