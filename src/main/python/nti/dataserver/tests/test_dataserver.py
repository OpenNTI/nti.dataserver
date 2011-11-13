#!/usr/bin/env python2.7

import unittest

from hamcrest import assert_that, equal_to, is_, none

from mock_dataserver import MockDataserver, WithMockDS

import nti.dataserver.users as users
import nti.dataserver.contenttypes as contenttypes



class TestDataserver( unittest.TestCase ):

	@WithMockDS
	def test_find_content_type( self ):
		ds =  MockDataserver.get_shared_dataserver()
		# is_ doesn't work, that turns into class assertion
		assert_that( ds.find_content_type( 'Notes' ), equal_to( contenttypes.Note ) )
		assert_that( ds.find_content_type( 'Note' ), equal_to( contenttypes.Note ) )
		assert_that( ds.find_content_type( 'notes' ), equal_to( contenttypes.Note ) )

		assert_that( ds.find_content_type( 'quizresults' ), equal_to( contenttypes.quizresult ) )

		assert_that( ds.find_content_type( 'TestDataserver' ), is_( none() ) )
		TestDataserver.__external_can_create__ = True
		assert_that( ds.find_content_type( 'TestDataserver' ), equal_to( TestDataserver ) )
		del TestDataserver.__external_can_create__
