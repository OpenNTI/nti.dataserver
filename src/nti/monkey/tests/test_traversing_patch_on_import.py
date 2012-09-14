#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from hamcrest import assert_that
from hamcrest import is_
from nose.tools import assert_raises

from zope import interface
from zope.traversing import interfaces as trv_interfaces, api as trv_api

import nti.monkey.traversing_patch_on_import
import nti.tests

setUpModule = lambda: nti.tests.module_setup( set_up_packages=('zope.traversing',) )
tearDownModule = nti.tests.module_teardown

def test_patched_traversal_api():
	assert nti.monkey.traversing_patch_on_import._patched_traversing, "No fixed version exists"

	@interface.implementer(trv_interfaces.ITraversable)
	class BrokenTraversable(object):
		def traverse( self, name, furtherPath ):
			getattr( self, u'\u2019', None ) # Raise unicode error


	with assert_raises(trv_interfaces.TraversalError):
		# Not a unicode error
		trv_api.traverseName( BrokenTraversable(), '' )

	assert_that( trv_api.traverseName( BrokenTraversable(), '', default=1 ), is_( 1 ) )



	with assert_raises(trv_interfaces.TraversalError):
		# Not a unicode error
		trv_api.traverseName( object(), u'\u2019' )

	assert_that( trv_api.traverseName( object(), u'\u2019', default=1 ), is_( 1 ) )

	with assert_raises(trv_interfaces.TraversalError):
		# Not a unicode error
		trv_api.traverseName( {}, u'\u2019' )

	assert_that( trv_api.traverseName( {}, u'\u2019', default=1 ), is_( 1 ) )

	# Namespacing works. Note that namespace traversal ignores default values
	with assert_raises(trv_interfaces.TraversalError):
		assert_that( trv_api.traverseName( {}, u'++foo++bar', default=1 ), is_( 1 ) )
