#!/usr/bin/env python2.7
from hamcrest import (assert_that, is_)

import unittest

import nti.dataserver.library

class TestLibrary( unittest.TestCase ):

	def test_space_in_path( self ):

		library = nti.dataserver.library.Library( (('/Library/Foo With Spaces', True),) )
		ent = library.titles[0]
		assert_that( ent.root, is_( '/Foo%20With%20Spaces/' ) )
		assert_that( ent.icon, is_( '/Foo%20With%20Spaces/icons/Foo%20With%20Spaces-Icon.png' ) )



if __name__ == '__main__':
	unittest.main()
