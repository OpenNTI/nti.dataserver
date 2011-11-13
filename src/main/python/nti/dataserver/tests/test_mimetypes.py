import unittest
import sys
from hamcrest import assert_that, is_, none

from ..mimetype import nti_mimetype_class as class_name_from_content_type
from ..mimetype import nti_mimetype_from_object as as_mimetype

def test_content_type():
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

from ..interfaces import IFriendsList
from ..users import FriendsList

def test_mimetype_from_object():
	assert_that( as_mimetype( None ), is_( none() ) )
	assert_that( as_mimetype( '' ), is_( none() ) )

	FL_MT = 'application/vnd.nextthought.friendslist'
	# interface
	assert_that( as_mimetype( IFriendsList ), is_( FL_MT ) )
	# class that implements
	assert_that( as_mimetype( FriendsList ), is_( FL_MT ) )
	# instance
	assert_that( as_mimetype( FriendsList("My FL" ) ), is_( FL_MT ) )

if __name__ == '__main__':
	unittest.main(sys.argv[1:])
