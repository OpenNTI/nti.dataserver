#!/usr/bin/env python2.7
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property
from hamcrest import greater_than_or_equal_to


from webtest import TestApp

import os.path

import urllib

from nti.ntiids import ntiids

from nti.dataserver.tests import mock_dataserver

import anyjson as json

from .test_application import ApplicationTestBase
from .test_application import PersistentContainedExternal
from .test_application import ContainedExternal

from urllib import quote as UQ

class TestApplicationEnclosures(ApplicationTestBase):


	def test_class_trivial_enclosure_href(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )

			_create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )

		path = '/dataserver2/providers/OU/Classes/CS2051/'
		data = b'\xFF\xF0\x20\x98\xB1'
		res = testapp.post( path, data, headers=(('Content-Type','image/png'),), extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )


		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', UQ('/dataserver2/providers/OU/Classes/CS2051/++adapter++enclosures/SimplePersistentEnclosure' ) ) ) ) )

		res = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/++adapter++enclosures/SimplePersistentEnclosure', extra_environ=self._make_extra_environ() )
		assert_that( res.content_type, is_( 'image/png' ) )
		assert_that( res.body, is_( data ) )

		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', UQ( '/dataserver2/providers/OU/Classes/CS2051/++adapter++enclosures/SimplePersistentEnclosure' ) ) ) ) )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', UQ( '/dataserver2/providers/OU/Classes/CS2051/++adapter++enclosures/SimplePersistentEnclosure-2' ) ) ) ) )

		path = '/dataserver2/providers/OU/Classes'
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
#		from IPython.core.debugger import Tracer; debug_here = Tracer()()
		links = body['Items']['CS2051']['Links']
		assert_that( links, has_item( has_entry( 'href', UQ('/dataserver2/providers/OU/Classes/CS2051/++adapter++enclosures/SimplePersistentEnclosure' ) ) ) )

	def _check_class_modeled_enclosure_href( self, data, mime_type, check_get_with_objects=True ):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )

			_create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )

		# Modeled data
		path = '/dataserver2/providers/OU/Classes/CS2051/'

		data = json.dumps( data )
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': mime_type, 'Slug': 'TheSlug'})
		assert_that( res.status_int, is_( 201 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', UQ('/dataserver2/providers/OU/Classes/CS2051/++adapter++enclosures/TheSlug') ) ) ) )
		# The enclosure should have a valid NTIID
		if check_get_with_objects:
			enclosure_ntiid = body['Links'][0]['ntiid']
			_type = 'Objects' if check_get_with_objects else 'NTIIDs'
			res = testapp.get( '/dataserver2/' + _type + '/' + enclosure_ntiid, extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( res.content_type, is_( mime_type ) )
		return body, testapp

	def test_class_modeled_enclosure_href(self):
		data = { 'Class': 'ClassScript', 'body': ["The body"] }
		self._check_class_modeled_enclosure_href( data, 'application/vnd.nextthought.classscript+json' )


	def test_class_quiz_enclosure(self):
		# Notice that the ID must not result in being a valid NTIID,
		# because we need to be using the OID
		quiz_data = {"MimeType":"application/vnd.nextthought.quiz",
					 "Class": "Quiz",
					 "ID": "mathcounts-2011-0",
					 "Items": {"1" : { "Class": "QuizQuestion","Answers": ["$5$", "$5.0$"],
									   "MimeType": "application/vnd.nextthought.quizquestion","ID": "1", "Text": "foo bar" } } }

		quiz, testapp = self._check_class_modeled_enclosure_href( quiz_data, 'application/vnd.nextthought.quiz+json' )

		# We should be able to post a response for grading with raw strings
		result_data = {"Class": "QuizResult", "MimeType":"application/vnd.nextthought.quizresult",
					   "ContainerId": ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' ),
					   "QuizID": quiz['NTIID'],
					   'Items': {"1": "0"}}
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com/',
							   json.dumps( result_data ),
							   extra_environ=self._make_extra_environ() )
		# and with wrapped responses
		result_data = {"Class": "QuizResult", "MimeType":"application/vnd.nextthought.quizresult",
					   "ContainerId": ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' ),
					   "QuizID": quiz['NTIID'],
					   'Items': {"1": {"ID": "1", "Response": "0"}}}
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com/',
							   json.dumps( result_data ),
							   extra_environ=self._make_extra_environ() )


	@mock_dataserver.WithMockDS
	def test_class_section_modeled_enclosure_href(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			self._create_user(username='jason.madden@nextthought.com' )

			_create_class( self.ds, ('sjohnson@nextthought.com',) )
		testapp = TestApp( self.app )

			# Modeled data
		path = '/dataserver2/providers/OU/Classes/CS2051/CS2051.101'
		data = { 'Class': 'ClassScript', 'body': ["The body"] }
		data = json.dumps( data )
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.classscript', 'Slug': 'TheSlug'})
		assert_that( res.status_int, is_( 201 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', UQ('/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug' ) ) ) ) )

		# Getting just the classes is correct link as well
		res = testapp.get( '/dataserver2/providers/OU/Classes', extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		links = body['Items']['CS2051']['Sections'][0]['Links']
		assert_that( links, has_item( has_entry( 'href', UQ('/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug' ) ) ) )

		# Get it
		res = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug', extra_environ=self._make_extra_environ() )

		# Update it
		data = { 'Class': 'ClassScript', 'body': ["The body2"] }
		data = json.dumps( data )
		res = testapp.put( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug',
						 data,
						 headers={'Content-Type': 'application/vnd.nextthought.classscript', 'Slug': 'TheSlug'},
						 extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )

		# Update it via the Object URL...this goes through a different traversal,
		# finding the object not via container but via direct lookup, resulting in an ObjectcontainedResource
		# which gets us to the _UGD* views, not the _Enclosure* views.
		path = body['Links'][0]['href']
		assert_that( path, contains_string( 'Objects' ) )
		# FIXME: This is what we'd really like, though:
		#assert_that( path, is_( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug' ) )
		path = '/dataserver2/providers/OU/Objects/%s' % urllib.quote( body['OID'] )
		res = testapp.put( path,
							   data,
							   headers={'Content-Type': 'application/vnd.nextthought.classscript', 'Slug': 'TheSlug'},
							   extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )

		# Delete it via both URLs for the same reason as above
		# (TODO: This is no longer possible)
		# Delete it
		res = testapp.delete( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug', extra_environ=self._make_extra_environ() )
		assert_that( res, has_property( 'status_int', 204 ) )
		# Delete it
		#res = testapp.delete( path, extra_environ=self._make_extra_environ() )
		#assert_that( res, has_property( 'status_int', 204 ) )


		testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug',
					 extra_environ=self._make_extra_environ(),
					 status=404	)


	def test_class_section_trivial_enclosure_href(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )

			_create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )

		# Modeled data
		path = '/dataserver2/providers/OU/Classes/CS2051/CS2051.101'
		data = "This is the data"
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'text/plain', 'Slug': 'TheSlug'})
		assert_that( res.status_int, is_( 201 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', UQ('/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug' ) ) ) ) )

		# Get it
		res = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug', extra_environ=self._make_extra_environ() )

		# Update it
		data = "This is the new data"
		testapp.put( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug',
					 data,
					 extra_environ=self._make_extra_environ() )

		# Delete it
		res = testapp.delete( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug', extra_environ=self._make_extra_environ() )
		assert_that( res, has_property( 'status_int', 204 ) )


		testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/++adapter++enclosures/TheSlug',
					 extra_environ=self._make_extra_environ(),
					 status=404	)


from .test_application import _create_class
