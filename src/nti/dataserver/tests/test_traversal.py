#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import


#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that, is_
from hamcrest import contains_string
from nose.tools import assert_raises
import zope.testing.loghandler

from zope import interface
from zope.location import interfaces as loc_interfaces

from nti.dataserver import traversal

from .mock_dataserver import DataserverLayerTest

class TestTraversal(DataserverLayerTest):

	def test_unicode_resource_path(self):

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


	def test_traversal_no_root(self):
		@interface.implementer(loc_interfaces.ILocation)
		class Middle(object):
			__parent__ = None
			__name__ = u'Middle'

		@interface.implementer(loc_interfaces.ILocation)
		class Leaf(object):
			__parent__ = Middle()
			__name__ = u'\u2019'

		log_handler = zope.testing.loghandler.Handler(None)
		log_handler.add( 'nti.dataserver.traversal' )
		try:
			with assert_raises( TypeError ):
				traversal.resource_path( Leaf() )
			record, = log_handler.records
			assert_that( record.getMessage(), contains_string( "test_traversal.Middle" ) )
		finally:
			log_handler.close()
