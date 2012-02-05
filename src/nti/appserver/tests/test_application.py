#!/usr/bin/env python2.7
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item,
					  contains_string, ends_with, all_of, has_entries)

from hamcrest.library import has_property
from nti.appserver.application import createApplication
from nti.dataserver.library import Library
import nti.contentsearch
import nti.contentsearch.interfaces
import pyramid.config
import pyramid.httpexceptions as hexc

from nti.appserver.tests import ConfiguringTestBase
from webtest import TestApp

import os
import os.path

import urllib
from nti.dataserver import users, ntiids, providers, classes
from nti.dataserver.datastructures import ContainedMixin, to_external_ntiid_oid
from nti.dataserver import contenttypes, datastructures, interfaces as nti_interfaces

from nti.dataserver.tests import mock_dataserver

import anyjson as json

from persistent import Persistent
from zope import interface

class ContainedExternal(ContainedMixin):

	def toExternalObject( self ):
		return str(self)

class PersistentContainedExternal(ContainedExternal,Persistent):
	pass

class ApplicationTestBase(ConfiguringTestBase):

	def _setup_library(self):
		return Library()

	def setUp(self):
		super(ApplicationTestBase,self).setUp()
		self.ds = mock_dataserver.MockDataserver()
		self.app, self.main = createApplication( 8080, self._setup_library(), create_ds=self.ds, pyramid_config=self.config )
		root = '/Library/WebServer/Documents/'
		# We'll volunteer to serve all the files in the root directory
		# This SHOULD include 'prealgebra' and 'mathcounts'
		serveFiles = [ ('/' + s, os.path.join( root, s) )
					   for s in os.listdir( root )
					   if os.path.isdir( os.path.join( root, s ) )]
		self.main.setServeFiles( serveFiles )

	def _make_extra_environ(self, user=b'sjohnson@nextthought.com', **kwargs):
		result = {
			b'HTTP_AUTHORIZATION': b'Basic ' + (user + ':temp001').encode('base64'),
			}
		for k, v in kwargs.items():
			k = str(k)
			k.replace( '_', '-' )
			result[k] = v

		return result


class TestApplication(ApplicationTestBase):


	# FIXME: This shouldn't be necessary. But the SocketIOHandler
	# part of the AppServer is currently dealing with transactions.
	# Migrate to pyramid_tm
	@mock_dataserver.WithMockDSTrans
	def test_path_with_parens(self):
		contained = ContainedExternal()
		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		user.addContainedObject( contained )
		assert_that( user.getContainer( contained.containerId ), has_length( 2 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + contained.containerId + ')/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str(contained) ) )

	@mock_dataserver.WithMockDSTrans
	def test_pages_with_only_shared_not_404(self):
		contained = PersistentContainedExternal()
		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		user.addContainedObject( contained )
		assert_that( user.getContainer( contained.containerId ), has_length( 2 ) )

		user2 = users.User.create_user( self.ds, username='foo@bar' )
		user2._addSharedObject( contained )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/foo@bar/Pages(' + contained.containerId + ')/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))

		assert_that( res.body, contains_string( str(contained) ) )

	@mock_dataserver.WithMockDSTrans
	def test_deprecated_path_with_slash(self):
		contained = ContainedExternal()
		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		user.addContainedObject( contained )
		assert_that( user.getContainer( contained.containerId ), has_length( 2 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/' + contained.containerId + '/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str(contained) ) )


	@mock_dataserver.WithMockDS
	def test_post_pages_collection(self):
		with self.ds.dbTrans():
			user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
			testapp = TestApp( self.app )
			containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			data = json.serialize( { 'Class': 'Highlight',
									 'ContainerId': containerId,
									 'Location': 'foo-bar'} )

			path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
			res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
			assert_that( res.status_int, is_( 201 ) )
			assert_that( res.body, contains_string( '"Location": "foo-bar"' ) )
			assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson%40nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
			assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )

			path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + containerId + ')/UserGeneratedData'
			res = testapp.get( path, extra_environ=self._make_extra_environ())
			assert_that( res.body, contains_string( '"Location": "foo-bar"' ) )

		with self.ds.dbTrans():
			# The pages collection should have complete URLs
			path = '/dataserver2/users/sjohnson@nextthought.com/Pages'
			res = testapp.get( path, extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			links = body['Collection']['Links']
			assert_that( links, has_item( has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Search/RecursiveUserGeneratedData' ) ) )
			assert_that( body, has_entry( 'Items', has_length( 2 ) ) )
			for item in body['Items']:
				item_id = item['ID']
				links = item['Links']
				assert_that( links, has_item( has_entry( 'href',
														 urllib.quote( '/dataserver2/users/sjohnson@nextthought.com/Pages(%s)/RecursiveStream' % item_id ) ) ) )


	@mock_dataserver.WithMockDSTrans
	def test_user_search(self):
		contained = ContainedExternal()
		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		user.addContainedObject( contained )
		assert_that( user.getContainer( contained.containerId ), has_length( 2 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str('sjohnson@nextthought.com') ) )
		# We should have an edit link
		body = json.loads( res.body )
		assert_that( body['Items'][0], has_entry( 'Links',
												  has_item( all_of(
													  has_entry( 'href', starts_with( "/dataserver2/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID" ) ),
													  has_entry( 'rel', 'edit' ) ) ) ) )

	@mock_dataserver.WithMockDSTrans
	def test_user_search_deprecated_path(self):
		contained = ContainedExternal()
		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		user.addContainedObject( contained )
		assert_that( user.getContainer( contained.containerId ), has_length( 2 ) )

		testapp = TestApp( self.app )
		path = '/dataserver/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str('sjohnson@nextthought.com') ) )

	@mock_dataserver.WithMockDSTrans
	def test_search_empty_term_user_ugd_book(self):
		"Searching with an empty term returns empty results"
		contained = ContainedExternal()
		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		user.addContainedObject( contained )
		assert_that( user.getContainer( contained.containerId ), has_length( 2 ) )

		testapp = TestApp( self.app )
		# The results are not defined across the search types,
		# we just test that it doesn't raise a 404
		for search_path in ('UserSearch','users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData'):
			for ds_path in ('dataserver', 'dataserver2'):
				path = '/' + ds_path +'/' + search_path + '/'
				res = testapp.get( path, extra_environ=self._make_extra_environ())
				assert_that( res.status_int, is_( 200 ) )

	@mock_dataserver.WithMockDSTrans
	def test_ugd_search_no_data_returns_empty(self):
		"Any search term against a user whose index DNE returns empty results"

		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		testapp = TestApp( self.app )
		for search_term in ('', 'term'):
			for ds_path in ('dataserver', 'dataserver2'):
				path = '/' + ds_path +'/users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData/' + search_term
				res = testapp.get( path, extra_environ=self._make_extra_environ())
				assert_that( res.status_int, is_( 200 ) )

		# This should not have created index entries for the user.
		# (Otherwise, theres denial-of-service possibilities)
		ixman = pyramid.config.global_registries.last.getUtility( nti.contentsearch.interfaces.IIndexManager )
		with ixman.dbTrans():
			assert_that( ixman.get_user_index_manager( 'user@dne.org', create=False ), is_( none() ) )

	@mock_dataserver.WithMockDSTrans
	def test_ugd_search_other_user(self):
		"Security prevents searching other user's data"

		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		testapp = TestApp( self.app )
		for search_term in ('', 'term'):
			for ds_path in ('dataserver', 'dataserver2'):
				path = '/' + ds_path +'/users/user@dne.org/Search/RecursiveUserGeneratedData/' + search_term
				with self.assertRaises(hexc.HTTPForbidden):
					testapp.get( path, extra_environ=self._make_extra_environ())


		# This should not have created index entries for the user.
		# (Otherwise, theres denial-of-service possibilities)
		ixman = pyramid.config.global_registries.last.getUtility( nti.contentsearch.interfaces.IIndexManager )
		with ixman.dbTrans():
			assert_that( ixman.get_user_index_manager( 'user@dne.org', create=False ), is_( none() ) )


	@mock_dataserver.WithMockDSTrans
	def test_create_friends_list_content_type(self):
		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		testapp = TestApp( self.app )
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["troy.daley@nextthought.com"],"realname":"boom"}'

		path = '/dataserver2/users/sjohnson@nextthought.com/FriendsLists/'

		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"boom@nextthought.com"' ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

	@mock_dataserver.WithMockDSTrans
	def test_edit_note_returns_editlink(self):
		"The object returned by POST should have enough ACL to regenerate its Edit link"
		user = users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		n = contenttypes.Note()
		n.containerId = 'tag:nti:foo'
		user.addContainedObject( n )
		testapp = TestApp( self.app )
		data = '{"body": ["text"]}'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % datastructures.to_external_ntiid_oid( n )
		path = urllib.quote( path )
		res = testapp.put( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( json.loads(res.body), has_entry( 'href', path ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'edit' ) ) ) )


	@mock_dataserver.WithMockDSTrans
	def test_meth_not_allowed(self):
		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		with self.assertRaises(hexc.HTTPMethodNotAllowed):
			testapp.get( path, status=405, extra_environ=self._make_extra_environ())


	@mock_dataserver.WithMockDSTrans
	def test_class_provider_hrefs(self):
		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		users.User.create_user( self.ds, username='jason.madden@nextthought.com' )

		clazz = _create_class( self.ds, ('sjohnson@nextthought.com',) )
		testapp = TestApp( self.app )
		body = testapp.get( '/dataserver2/providers/OU/Classes/CS2051', extra_environ=self._make_extra_environ() )

		body = json.loads( body.text )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.classinfo' ) )
		# The edit href is complete
		assert_that( body, has_entry( 'Links',
									  has_item( has_entries( rel='edit',
															 href='/dataserver2/providers/OU/Objects/%s' % urllib.quote(to_external_ntiid_oid(clazz)) ) ) ) )
		# And the top-level href matches the edit href
		assert_that( body, has_entry( 'href', body['Links'][0]['href'] ) )


		body = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101', extra_environ=self._make_extra_environ() )

		body = json.loads( body.text )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.sectioninfo' ) )
		assert_that( body, has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/CS2051.101' ) )

		# We should be able to resolve the parent class of this section
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'rel', 'parent' ) ) ) )
		class_url = body['Links'][0]['href']
		assert_that( class_url, ends_with( 'OU-Class-CS2051' ) ) # NTIID URL
		body = testapp.get( class_url, extra_environ=self._make_extra_environ() )
		json.loads( body.text )

		# When fetched as a collection, they still have edit info

		body = testapp.get( '/dataserver2/providers/OU/Classes/', extra_environ=self._make_extra_environ() )
		body = json.loads( body.text )
		assert_that( body, has_entry( 'href', '/dataserver2/providers/OU/Classes' ) )

		assert_that( body, has_entry( 'Items', has_length( 1 ) ) )

		body = body['Items']['CS2051']
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.classinfo' ) )
		# The edit href is complete
		assert_that( body, has_entry( 'Links',
									  has_item( has_entries( rel='edit',
															 href='/dataserver2/providers/OU/Classes/CS2051' ) ) ) )
		# And the top-level href matches the edit href
		assert_that( body, has_entry( 'href', body['Links'][0]['href'] ) )

	@mock_dataserver.WithMockDSTrans
	def _do_post_class_to_path(self, path):
		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		_create_class( self.ds, ('sjohnson@nextthought.com',) )
		testapp = TestApp( self.app )
		data = json.serialize( { 'Class': 'ClassInfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2502'} )

		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2502' ) )

	@mock_dataserver.WithMockDSTrans
	def _do_post_class_to_path_with_section(self, path, get=None):
		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		_create_class( self.ds, ('sjohnson@nextthought.com',) )
		testapp = TestApp( self.app )
		data = json.serialize( { 'Class': 'ClassInfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503' } )


		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )

		data = json.serialize( { 'Class': 'ClassInfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503',
								 'Sections': [{'ID': 'CS2503.101', 'Class': 'SectionInfo', 'Enrolled': ['jason.madden@nextthought.com']}]} )
		res = testapp.put( path + 'CS2503', data, extra_environ=self._make_extra_environ() )

		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2503' ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

		if get:
			res = testapp.get( path + 'CS2503', extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( body, has_entry( 'ID', 'CS2503' ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

	def test_post_class_full_path(self):
		self._do_post_class_to_path( '/dataserver2/providers/OU/Classes/' )
		self._do_post_class_to_path_with_section( '/dataserver2/providers/OU/Classes/', get=True )

	def test_post_class_part_path(self):
		self._do_post_class_to_path( '/dataserver2/providers/OU/' )


	@mock_dataserver.WithMockDS
	def test_class_trivial_enclosure_href(self):
		with self.ds.dbTrans():
			users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
			users.User.create_user( self.ds, username='jason.madden@nextthought.com' )

			_create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )

		path = '/dataserver2/providers/OU/Classes/CS2051/'
		data = 'The simple data'
		with self.ds.dbTrans():
			res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
			assert_that( res.status_int, is_( 201 ) )

		with self.ds.dbTrans():
			res = testapp.get( path, extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/SimplePersistentEnclosure' ) ) ) )

		with self.ds.dbTrans():
			res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
			assert_that( res.status_int, is_( 201 ) )

		with self.ds.dbTrans():
			res = testapp.get( path, extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/SimplePersistentEnclosure' ) ) ) )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/SimplePersistentEnclosure-2' ) ) ) )


	def _check_class_modeled_enclosure_href( self, data, mime_type, check_get_with_objects=True ):
		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		users.User.create_user( self.ds, username='jason.madden@nextthought.com' )

		_create_class( self.ds, ('sjohnson@nextthought.com',) )
		testapp = TestApp( self.app )

		# Modeled data
		path = '/dataserver2/providers/OU/Classes/CS2051/'

		data = json.dumps( data )
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': mime_type, 'Slug': 'TheSlug'})
		assert_that( res.status_int, is_( 201 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/TheSlug' ) ) ) )
		# The enclosure should have a valid NTIID
		if check_get_with_objects:
			enclosure_ntiid = body['Links'][0]['ntiid']
			_type = 'Objects' if check_get_with_objects else 'NTIIDs'
			res = testapp.get( '/dataserver2/' + _type + '/' + enclosure_ntiid, extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( res.content_type, is_( mime_type ) )
		return body, testapp

	@mock_dataserver.WithMockDSTrans
	def test_class_modeled_enclosure_href(self):
		data = { 'Class': 'ClassScript', 'body': ["The body"] }
		self._check_class_modeled_enclosure_href( data, 'application/vnd.nextthought.classscript+json' )

	@mock_dataserver.WithMockDSTrans
	def test_class_quiz_enclosure(self):
		# Notice that the ID must not result in being a valid NTIID,
		# because we need to be using the OID
		quiz_data = {"MimeType":"application/vnd.nextthought.quiz",
					 "Class": "Quiz",
					 "ID": "mathcounts-2011-0",
					 "Items": {"1" : { "Class": "QuizQuestion","Answers": ["$5$", "$5.0$"],
									   "MimeType": "application/vnd.nextthought.quizquestion","ID": "1", "Text": "foo bar" } } }

		quiz, testapp = self._check_class_modeled_enclosure_href( quiz_data, 'application/vnd.nextthought.quiz+json' )

		# We should be able to post a response for grading
		result_data = {"Class": "QuizResult",
					   "ContainerId": ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' ),
					   "QuizID": quiz['NTIID'],
					   'Items': {"1": "0"}}
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com/',
							   json.dumps( result_data ),
							   extra_environ=self._make_extra_environ() )


	@mock_dataserver.WithMockDSTrans
	def test_quiz_container_id_auto_mapping(self):
		# The quiz may live in any container
		quiz_data = {"MimeType":"application/vnd.nextthought.quiz",
					 'ContainerId': ntiids.make_ntiid( provider='mathcounts', nttype='HTML', specific='0' ),
					 "Class": "Quiz",
					 "ID": ntiids.make_ntiid( provider='sjohnson@nextthought.com', nttype=ntiids.TYPE_QUIZ, specific='0' ),
					 "Items": {"1" : { "Class": "QuizQuestion","Answers": ["$5$", "$5.0$"],
									   "MimeType": "application/vnd.nextthought.quizquestion","ID": "1", "Text": "foo bar" } } }
		testapp = TestApp( self.app )
		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com/Pages',
							json.dumps(quiz_data ),
							extra_environ=self._make_extra_environ() )
		json.loads( res.body )

		container_id = ntiids.make_ntiid( provider='sjohnson@nextthought.com', nttype=ntiids.TYPE_HTML, specific='0' )
		# We should be able to post a response for grading
		result_data = {"Class": "QuizResult",
					   "ContainerId": container_id,
					   'Items': {"1": "0"}}
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com/',
							   json.dumps( result_data ),
							   extra_environ=self._make_extra_environ() )


	@mock_dataserver.WithMockDS
	def test_class_section_modeled_enclosure_href(self):
		with self.ds.dbTrans():
			users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
			users.User.create_user( self.ds, username='jason.madden@nextthought.com' )

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
			assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug' ) ) ) )

		with self.ds.dbTrans():
			# Get it
			res = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug', extra_environ=self._make_extra_environ() )

			# Update it
			data = { 'Class': 'ClassScript', 'body': ["The body2"] }
			data = json.dumps( data )
			res = testapp.put( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug',
						 data,
						 headers={'Content-Type': 'application/vnd.nextthought.classscript', 'Slug': 'TheSlug'},
						 extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )

			# Update it via the Object URL...this goes through a different traversal,
			# finding the object not via container but via direct lookup, resulting in an ObjectcontainedResource
			# which gets us to the _UGD* views, not the _Enclosure* views.
			path = body['Links'][0]['href']
			assert_that( path, contains_string( 'Objects' ) )
			res = testapp.put( path,
							   data,
							   headers={'Content-Type': 'application/vnd.nextthought.classscript', 'Slug': 'TheSlug'},
							   extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )

		# Delete it via both URLs for the same reason as above
		class Doomed(Exception): pass
		with self.assertRaises(Doomed):
			with self.ds.dbTrans():
				# Delete it
				res = testapp.delete( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug', extra_environ=self._make_extra_environ() )
				assert_that( res, has_property( 'status_int', 204 ) )
				# Roll this transaction back :)
				raise Doomed()


		with self.ds.dbTrans():
			# Delete it
			res = testapp.delete( path, extra_environ=self._make_extra_environ() )
			assert_that( res, has_property( 'status_int', 204 ) )


		with self.ds.dbTrans():
			with self.assertRaises(hexc.HTTPNotFound):
				testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug',
							 extra_environ=self._make_extra_environ() )

	@mock_dataserver.WithMockDSTrans
	def test_class_section_trivial_enclosure_href(self):
		users.User.create_user( self.ds, username='sjohnson@nextthought.com' )
		users.User.create_user( self.ds, username='jason.madden@nextthought.com' )

		_create_class( self.ds, ('sjohnson@nextthought.com',) )
		testapp = TestApp( self.app )

		# Modeled data
		path = '/dataserver2/providers/OU/Classes/CS2051/CS2051.101'
		data = "This is the data"
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'text/plain', 'Slug': 'TheSlug'})
		assert_that( res.status_int, is_( 201 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug' ) ) ) )

		# Get it
		res = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug', extra_environ=self._make_extra_environ() )

		# Update it
		data = "This is the new data"
		testapp.put( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug',
					 data,
					 extra_environ=self._make_extra_environ() )

		# Delete it
		res = testapp.delete( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug', extra_environ=self._make_extra_environ() )
		assert_that( res, has_property( 'status_int', 204 ) )

		with self.assertRaises(hexc.HTTPNotFound):
			testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug',
						 extra_environ=self._make_extra_environ() )


def _create_class(ds, usernames_to_enroll=()):
	provider = providers.Provider( 'OU' )
	ds.root['providers']['OU'] = provider
	klass = provider.maybeCreateContainedObjectWithType(  'Classes', None )
	klass.containerId = 'Classes'
	klass.ID = 'CS2051'
	klass.Description = 'CS Class'
	with ds.dbTrans() as txn:
		txn._p_jar.add( klass )

	section = classes.SectionInfo()
	section.ID = 'CS2051.101'
	klass.add_section( section )
	section.InstructorInfo = classes.InstructorInfo()
	for user in usernames_to_enroll:
		section.enroll( user )
	section.InstructorInfo.Instructors.append( 'jason.madden@nextthought.com' )
	section.InstructorInfo.Instructors.append( 'sjohnson@nextthought.com' )
	section.Provider = 'OU'
	provider.addContainedObject( klass )

	assert_that( provider, has_property( '__parent__', ds.root['providers'] ) )
	return klass

class TestApplicationLibrary(ApplicationTestBase):
	child_ntiid = ntiids.make_ntiid( provider='ou', specific='test2', nttype='HTML' )

	def _setup_library(self):

		class NID(object):
			interface.implements( nti_interfaces.ILibraryTOCEntry )
			ntiid = TestApplicationLibrary.child_ntiid
			href = 'sect_0002.html'
			__parent__ = None
			__name__ = 'The name'
			def with_parent( self, p ):
				self.__parent__ = p
				return self

		class LibEnt(object):
			interface.implements( nti_interfaces.ILibraryEntry )
			root = '/prealgebra/'

		class Lib(object):
			interface.implements( nti_interfaces.ILibrary )
			titles = ()
			def pathToNTIID( self, ntiid ):
				return [NID().with_parent( LibEnt() )] if ntiid == TestApplicationLibrary.child_ntiid else None

		return Lib()

	@mock_dataserver.WithMockDSTrans
	def test_library_redirect(self):

		testapp = TestApp( self.app )
		# Unauth gets nothing
		with self.assertRaises( hexc.HTTPForbidden ):
			res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 302 ) )
		assert_that( res.headers, has_entry( 'Location', 'http://localhost/prealgebra/sect_0002.html' ) )



