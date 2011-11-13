#!/usr/bin/env python2.7

import unittest
from hamcrest import (assert_that, is_, none)

from nti.appserver.dataserver_pyramid_views import class_name_from_content_type

class TestClassFromContent(unittest.TestCase):

	def test_content_type(self):

		assert_that( class_name_from_content_type( None ), is_( none() ) )
		assert_that( class_name_from_content_type( 'text/plain' ), is_( none() ) )

		assert_that( class_name_from_content_type( 'application/vnd.nextthought+json' ), is_( none() ) )

		assert_that( class_name_from_content_type( 'application/vnd.nextthought.class+json' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.version.class+json' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.class' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.version.flag.class' ),
					 is_( 'class' ) )
