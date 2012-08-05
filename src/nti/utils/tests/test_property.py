#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from ..property import dict_alias

from hamcrest import assert_that
from hamcrest import has_property

def test_dict_alias():
	class X(object):
		def __init__( self ):
			self.x = 1

		y = dict_alias( 'x' )

	assert_that( X(), has_property( 'y', 1 ) )
	x = X()
	x.y = 2
	assert_that( x, has_property( 'y', 2 ) )
	assert_that( x, has_property( 'x', 2 ) )
