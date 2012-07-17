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

from nti.appserver.application import createApplication
from nti.contentlibrary.filesystem import Library
from nti.contentlibrary import interfaces as lib_interfaces
import nti.contentsearch
import nti.contentsearch.interfaces
import pyramid.config
import pyramid.httpexceptions as hexc

from nti.appserver.tests import ConfiguringTestBase
from webtest import TestApp
import webob.datetime_utils
import datetime

import os
import os.path

import urllib
from nti.dataserver import users, classes, providers
from nti.ntiids import ntiids
from nti.dataserver.datastructures import ContainedMixin, ZContainedMixin
from nti.externalization.oids import to_external_ntiid_oid
from nti.contentrange import contentrange
from nti.dataserver import contenttypes
from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.tests import mock_dataserver

import anyjson as json

from persistent import Persistent
from zope import interface
from zope import component
from zope.deprecation import __show__

class ContainedExternal(ZContainedMixin):

	def toExternalObject( self ):
		return str(self)

class PersistentContainedExternal(ContainedExternal,Persistent):
	pass

class ApplicationTestBase(ConfiguringTestBase):

	set_up_packages = () # None, because configuring the app will do this

	def _setup_library(self, *args, **kwargs):
		return Library()

	def setUp(self):
		__show__.off()
		super(ApplicationTestBase,self).setUp()
		#self.ds = mock_dataserver.MockDataserver()
		self.app, self.main = createApplication( 8080, self._setup_library(), create_ds=mock_dataserver.MockDataserver, pyramid_config=self.config, devmode=True )
		self.ds = component.getUtility( nti_interfaces.IDataserver )
		root = '/Library/WebServer/Documents/'
		# We'll volunteer to serve all the files in the root directory
		# This SHOULD include 'prealgebra' and 'mathcounts'
		serveFiles = [ ('/' + s, os.path.join( root, s) )
					   for s in os.listdir( root )
					   if os.path.isdir( os.path.join( root, s ) )]
		self.main.setServeFiles( serveFiles )
	def tearDown(self):
		__show__.on()
		super(ApplicationTestBase,self).tearDown()

	def _make_extra_environ(self, user=b'sjohnson@nextthought.com', **kwargs):
		result = {
			b'HTTP_AUTHORIZATION': b'Basic ' + (user + ':temp001').encode('base64'),
			}
		for k, v in kwargs.items():
			k = str(k)
			k.replace( '_', '-' )
			result[k] = v

		return result

	def _create_user(self, username=b'sjohnson@nextthought.com', password='temp001' ):
		return users.User.create_user( self.ds, username=username, password=password )


class TestApplication(ApplicationTestBase):

	def test_logon_ping(self):
		testapp = TestApp( self.app )
		testapp.get( '/dataserver2/logon.ping' )

	def test_path_with_parens(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = ContainedExternal()
			user = self._create_user( )
			contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + contained.containerId + ')/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str(contained) ) )

	def test_pages_with_only_shared_not_404(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = PersistentContainedExternal()
			user = self._create_user()
			contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

			user2 = self._create_user( username='foo@bar' )
			user2._addSharedObject( contained )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/foo@bar/Pages(' + contained.containerId + ')/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ(user='foo@bar'))

		assert_that( res.body, contains_string( str(contained) ) )


	def test_deprecated_path_with_slash(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = ContainedExternal()
			user = self._create_user()
			contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/' + contained.containerId + '/UserGeneratedData'
		#path = urllib.quote( path )
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.body, contains_string( str(contained) ) )



	def test_post_pages_collection(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()
			testapp = TestApp( self.app )
			containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			data = json.serialize( { 'Class': 'Highlight', 'MimeType': 'application/vnd.nextthought.highlight',
									 'ContainerId': containerId,
									 'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson%40nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages(' + containerId + ')/UserGeneratedData'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )


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

	def test_get_highlight_by_oid_has_links(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()

		testapp = TestApp( self.app )
		containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
		data = json.serialize( { 'Class': 'Highlight', 'MimeType': 'application/vnd.nextthought.highlight',
								 'ContainerId': containerId,
								 'applicableRange': {'Class': 'ContentRangeDescription'}} )

		path = '/dataserver2/users/sjohnson@nextthought.com/Pages/'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"Class": "ContentRangeDescription"' ) )
		assert_that( res.headers, has_entry( 'Location', contains_string( 'http://localhost/dataserver2/users/sjohnson%40nextthought.com/Objects/tag:nextthought.com,2011-10:sjohnson@nextthought.com-OID' ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.highlight+json' ) ) )


		path = res.headers['Location']
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_(200) )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links',
									  has_item( all_of(
										  has_entry( 'href', contains_string( '/dataserver2/users/sjohnson%40nextthought.com/Objects/tag' ) ),
										  has_entry( 'rel', 'edit' ) ) ) ))


	def test_post_two_friendslist_same_name(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'FriendsList',  'MimeType': 'application/vnd.nextthought.friendslist',
								 'ContainerId': 'FriendsLists',
								 'ID': "Foo@bar" } )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		testapp.post( path, data, extra_environ=self._make_extra_environ() )
		# Generates a conflict the next time
		testapp.post( path, data, extra_environ=self._make_extra_environ(), status=409 )


	def test_friends_list_uncached(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/FriendsLists', extra_environ=self._make_extra_environ() )
		assert_that( res.cache_control, has_property( 'no_store', True ) )

	def test_post_device(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'Device', 'MimeType': 'application/vnd.nextthought.device',
								 'ContainerId': 'Devices',
								 'ID': "deadbeef" } )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.device' ) )
		# Generates a conflict the next time
		testapp.post( path, data, extra_environ=self._make_extra_environ(), status=409 )

	def test_put_device(self):
		"Putting a non-existant device is not possible"
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()


		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'Device',
								 'ContainerId': 'Devices',
								 'ID': "deadbeef" } )
		path = '/dataserver2/users/sjohnson@nextthought.com/Devices/deadbeef'
		testapp.put( path, data, extra_environ=self._make_extra_environ(), status=404 )
		# But we can post it
		testapp.post( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )
		# And then put
		testapp.put( path, data, extra_environ=self._make_extra_environ(), status=200 )


	def test_user_search(self):
		with mock_dataserver.mock_db_trans(self.ds):
			contained = ContainedExternal()
			user = self._create_user()
			contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2', extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_item( all_of(
															has_entry( 'Title', 'Global' ),
															has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/UserSearch' ) ) ) ) ) )
		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.content_type, is_( 'application/vnd.nextthought+json' ) )
		assert_that( res.cache_control, has_property( 'no_store', True ) )

		assert_that( res.body, contains_string( str('sjohnson@nextthought.com') ) )
		# We should have an edit link
		body = json.loads( res.body )
		assert_that( body['Items'][0], has_entry( 'Links',
												  has_item( all_of(
													  has_entry( 'href', "/dataserver2/users/sjohnson%40nextthought.com" ),
													  has_entry( 'rel', 'edit' ) ) ) ) )


	def test_search_empty_term_user_ugd_book(self):
		"Searching with an empty term returns empty results"
		with mock_dataserver.mock_db_trans( self.ds ):
			contained = ContainedExternal()
			user = self._create_user()
			contained.containerId = ntiids.make_ntiid( provider='OU', nttype=ntiids.TYPE_MEETINGROOM, specific='1234' )
			user.addContainedObject( contained )
			assert_that( user.getContainer( contained.containerId ), has_length( 1 ) )

		testapp = TestApp( self.app )
		# The results are not defined across the search types,
		# we just test that it doesn't raise a 404
		for search_path in ('UserSearch','users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData'):
			for ds_path in ('dataserver2',):
				path = '/' + ds_path +'/' + search_path + '/'
				res = testapp.get( path, extra_environ=self._make_extra_environ())
				assert_that( res.status_int, is_( 200 ) )


	def test_ugd_search_no_data_returns_empty(self):
		"Any search term against a user whose index DNE returns empty results"
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )
		for search_term in ('', 'term'):
			for ds_path in ('dataserver2', ):
				path = '/' + ds_path +'/users/sjohnson@nextthought.com/Search/RecursiveUserGeneratedData/' + search_term
				res = testapp.get( path, extra_environ=self._make_extra_environ())
				assert_that( res.status_int, is_( 200 ) )

		# This should not have created index entries for the user.
		# (Otherwise, theres denial-of-service possibilities)
		with component.getUtility( nti_interfaces.IDataserverTransactionContextManager )():
			ixman = pyramid.config.global_registries.last.getUtility( nti.contentsearch.interfaces.IIndexManager )
			assert_that( ixman._get_user_index_manager( 'user@dne.org', create=False ), is_( none() ) )
			assert_that( ixman._get_user_index_manager( 'sjohnson@nextthought.com', create=False ), is_( none() ) )

	def test_ugd_search_other_user(self):
		"Security prevents searching other user's data"
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()


		testapp = TestApp( self.app )
		for search_term in ('', 'term'):
			for ds_path in ('dataserver2',):
				path = '/' + ds_path +'/users/user@dne.org/Search/RecursiveUserGeneratedData/' + search_term
				testapp.get( path, extra_environ=self._make_extra_environ(), status=403)


		# This should not have created index entries for the user.
		# (Otherwise, there's denial-of-service possibilities)
		ixman = pyramid.config.global_registries.last.getUtility( nti.contentsearch.interfaces.IIndexManager )
		with component.getUtility( nti_interfaces.IDataserverTransactionContextManager )():
			assert_that( ixman._get_user_index_manager( 'user@dne.org', create=False ), is_( none() ) )
			assert_that( ixman._get_user_index_manager( 'sjohnson@nextthought.com', create=False ), is_( none() ) )



	def test_create_friends_list_content_type(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
		testapp = TestApp( self.app )
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["troy.daley@nextthought.com"],"realname":"boom"}'

		path = '/dataserver2/users/sjohnson@nextthought.com/FriendsLists/'

		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"boom@nextthought.com"' ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

		body = json.loads( res.body )
		assert_that( body, has_entry( 'href', starts_with('/dataserver2/users/sjohnson%40nextthought.com/Objects' ) ))
		#assert_that( body, has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/FriendsLists/boom%40nextthought.com' ) )

	def test_create_friends_list_post_user(self):
		# Like the previous test, but _UGDPostView wasn't consistent with where it was setting up the phony location proxies,
		# so we could get different results depending on where we came from
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
		testapp = TestApp( self.app )
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["troy.daley@nextthought.com"],"realname":"boom"}'

		path = '/dataserver2/users/sjohnson@nextthought.com'

		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.body, contains_string( '"boom@nextthought.com"' ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )

		body = json.loads( res.body )
		assert_that( body, has_entry( 'href', starts_with('/dataserver2/users/sjohnson%40nextthought.com/Objects' ) ))
		#assert_that( body, has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/FriendsLists/boom%40nextthought.com' ) )

	def test_post_friendslist_friends_field(self):
		"We can put to ++fields++friends"
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			self._create_user('troy.daley@nextthought.com')
		testapp = TestApp( self.app )
		# Make one
		data = '{"Last Modified":1323788728,"ContainerId":"FriendsLists","Username": "boom@nextthought.com","friends":["steve.johnson@nextthought.com"],"realname":"boom"}'
		path = '/dataserver2/users/sjohnson@nextthought.com'
		res = testapp.post( path, data, extra_environ=self._make_extra_environ(), headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )

		# Edit it
		data = '["troy.daley@nextthought.com"]'
		path = res.json_body['href'] + '/++fields++friends'

		res = testapp.put( str(path),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={'Content-Type': 'application/vnd.nextthought.friendslist+json' } )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'friends', has_item( has_entry( 'Username', 'troy.daley@nextthought.com' ) ) ) )
		assert_that( res.headers, has_entry( 'Content-Type', contains_string( 'application/vnd.nextthought.friendslist+json' ) ) )


	def test_edit_note_returns_editlink(self):
		"The object returned by POST should have enough ACL to regenerate its Edit link"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
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

	def test_like_unlike_note(self):
		"We get the appropriate @@like or @@unlike links for a note"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = 'tag:nti:foo'
			user.addContainedObject( n )

		testapp = TestApp( self.app )
		data = ''
		path = '/dataserver2/Objects/%s' % datastructures.to_external_ntiid_oid( n )
		path = urllib.quote( path )
		# Initially, unliked, I get asked to like
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )
		assert_that( json.loads(res.body),
					 has_entry( 'Links',
								has_item(
									has_entry(
										'href',
										'/dataserver2/Objects/' + urllib.quote(datastructures.to_external_ntiid_oid( n )) + '/@@like' ) ) ) )

		# So I do
		res = testapp.post( path + '/@@like', data, extra_environ=self._make_extra_environ() )
		# and now I'm asked to unlike
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 1 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unlike' ) ) ) )

		# Same again
		res = testapp.post( path + '/@@like', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unlike' ) ) ) )

		# And I can unlike
		res = testapp.post( path + '/@@unlike', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )

	def test_favorite_unfavorite_note(self):
		"We get the appropriate @@favorite or @@unfavorite links for a note"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = 'tag:nti:foo'
			user.addContainedObject( n )

		testapp = TestApp( self.app )
		data = ''
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % datastructures.to_external_ntiid_oid( n )
		path = urllib.quote( path )
		# Initially, unliked, I get asked to favorite
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'favorite' ) ) ) )

		# So I do
		res = testapp.post( path + '/@@favorite', data, extra_environ=self._make_extra_environ() )
		# and now I'm asked to unlike
		assert_that( res.status_int, is_( 200 ) )
		# like count doesn't change
		assert_that( res.json_body, has_entry( 'LikeCount',  0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unfavorite' ) ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )

		# Same again
		res = testapp.post( path + '/@@favorite', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'unfavorite' ) ) ) )

		# And I can unlike
		res = testapp.post( path + '/@@unfavorite', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )
		assert_that( json.loads(res.body), has_entry( 'Links', has_item( has_entry( 'rel', 'favorite' ) ) ) )

	def test_edit_note_sharing_only(self):
		"We can POST to a specific sub-URL to change the sharing"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = 'tag:nti:foo'
			user.addContainedObject( n )
			assert_that( n.sharingTargets, is_( set() ) )

		testapp = TestApp( self.app )
		data = '["Everyone"]'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % datastructures.to_external_ntiid_oid( n )
		field_path = path + '/sharedWith' # The name of the external field

		res = testapp.put( urllib.quote( field_path ),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" } )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.json_body, has_entry( "sharedWith", has_item( "Everyone" ) ) )

		assert_that( res.json_body, has_entry( 'href', urllib.quote( path ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'edit' ) ) ) )

	def _edit_user_ext_field( self, field, data ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app )

		# This works for both the OID and direct username paths
		for path in ('/dataserver2/Objects/%s' % datastructures.to_external_ntiid_oid( user ), '/dataserver2/users/' + user.username):

			field_path = path + '/' + field # The name of the external field

			res = testapp.put( urllib.quote( field_path ),
							   data,
							   extra_environ=self._make_extra_environ(),
							   headers={"Content-Type": "application/json" } )
			assert_that( res.status_int, is_( 200 ) )

			with mock_dataserver.mock_db_trans( self.ds ):
				# For the case where we change the password, we have to
				# recreate the user for the next loop iteration to work
				user.password = 'temp001'



	def test_edit_user_password_only(self):
		"We can POST to a specific sub-URL to change the password"
		data = '"newpassword"'
		self._edit_user_ext_field( 'password', data )

	def test_edit_user_count_only(self):
		"We can POST to a specific sub-URL to change the notification count"

		data = '5'
		self._edit_user_ext_field( 'NotificationCount', data )

	def test_put_data_to_user( self ):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app )

		# This works for both the OID and direct username paths
		for path in ('/dataserver2/Objects/%s' % datastructures.to_external_ntiid_oid( user ), '/dataserver2/users/' + user.username):

			data = json.dumps( {"NotificationCount": 5 } )

			res = testapp.put( urllib.quote( path ),
							   data,
							   extra_environ=self._make_extra_environ(),
							   headers={"Content-Type": "application/json" } )
			assert_that( res.status_int, is_( 200 ) )
			assert_that( res.json_body, has_entry( 'NotificationCount', 5 ) )



	def test_get_user_not_allowed(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()

		testapp = TestApp( self.app )
		path = '/dataserver2/users/sjohnson@nextthought.com'
		testapp.get( path, status=405, extra_environ=self._make_extra_environ())

	def test_class_provider_hrefs(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )

			clazz = _create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )
		body = testapp.get( '/dataserver2/providers/OU/Classes/CS2051', extra_environ=self._make_extra_environ() )

		body = json.loads( body.text )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.classinfo' ) )
		# The edit href is complete
		assert_that( body, has_entry( 'Links',
									  has_item( has_entries( rel='edit',
															 #href='/dataserver2/providers/OU/Classes/CS2051' ) ) ) )
															 href='/dataserver2/providers/OU/Objects/%s' % urllib.quote(to_external_ntiid_oid(clazz)) ) ) ) )
		# And the top-level href matches the edit href
		assert_that( body, has_entry( 'href', body['Links'][0]['href'] ) )

		body = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101', extra_environ=self._make_extra_environ() )

		body = json.loads( body.text )
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.sectioninfo' ) )
		#assert_that( body, has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/CS2051.101' ) )
		assert_that( body, has_entry( 'href', starts_with( '/dataserver2/providers/OU/Objects/tag' ) ) )

		# We should be able to resolve the parent class of this section
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'rel', 'parent' ) ) ) )
		class_url = body['Links'][0]['href']
		assert_that( class_url, ends_with( 'OU-Class-CS2051' ) ) # NTIID URL
		body = testapp.get( class_url, extra_environ=self._make_extra_environ() )
		json.loads( body.text )

		# When fetched as a collection, they still have edit info

		body = testapp.get( '/dataserver2/providers/OU/Classes/', extra_environ=self._make_extra_environ() )
		body = json.loads( body.text )
		assert_that( body, has_entry( 'href',
									 # '/dataserver2/providers/OU/Objects/%s' % urllib.quote(to_external_ntiid_oid(clazz))))
									  '/dataserver2/providers/OU/Classes' ) )

		assert_that( body, has_entry( 'Items', has_length( 1 ) ) )

		body = body['Items']['CS2051']
		assert_that( body, has_entry( 'MimeType', 'application/vnd.nextthought.classinfo' ) )
		# The edit href is complete
		assert_that( body, has_entry( 'Links',
									  has_item( has_entries( rel='edit',
															 #href='/dataserver2/providers/OU/Classes/CS2051' ) ) ) )
															 href='/dataserver2/providers/OU/Objects/%s' % urllib.quote(to_external_ntiid_oid(clazz)) ) ) ) )
		# And the top-level href matches the edit href
		assert_that( body, has_entry( 'href', body['Links'][0]['href'] ) )


	def _do_post_class_to_path(self, path):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			_create_class( self.ds, ('sjohnson@nextthought.com',) )
		testapp = TestApp( self.app )
		data = json.serialize( { 'Class': 'ClassInfo',  'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2502'} )

		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2502' ) )


	def _do_post_class_to_path_with_section(self, path, get=None):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			_create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )
		data = json.serialize( { 'Class': 'ClassInfo', 'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503' } )

		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )

		data = json.serialize( { 'Class': 'ClassInfo', 'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503',
								 'Sections': [{'ID': 'CS2503.101',
											   'Class': 'SectionInfo',  'MimeType': 'application/vnd.nextthought.sectioninfo',
											   'Enrolled': ['jason.madden@nextthought.com']}]} )
		res = testapp.put( path + 'CS2503', data, extra_environ=self._make_extra_environ() )

		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2503' ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

		if get:
			res = testapp.get( path + 'CS2503', extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( body, has_entry( 'ID', 'CS2503' ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

	def test_post_class_full_path(self):
		self._do_post_class_to_path( '/dataserver2/providers/OU/Classes/' )

	def test_post_class_full_path_section(self):
		self._do_post_class_to_path_with_section( '/dataserver2/providers/OU/Classes/', get=True )

	def test_post_class_part_path(self):
		self._do_post_class_to_path( '/dataserver2/providers/OU/' )


	def test_post_class_section_same_time(self):
		path = '/dataserver2/providers/OU/Classes/'
		get = True
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			_create_class( self.ds, ('sjohnson@nextthought.com',) )

		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'ClassInfo', 'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503',
								 'Sections': [{'ID': 'CS2503.101',
											   'Class': 'SectionInfo', 'MimeType': 'application/vnd.nextthought.sectioninfo',
											   'Enrolled': ['jason.madden@nextthought.com']}]} )
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )


		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2503' ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
		if get:
			res = testapp.get( path + 'CS2503', extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( body, has_entry( 'ID', 'CS2503' ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )

	def test_post_class_section_same_time_uncreated(self):
		path = '/dataserver2/providers/OU/'
		get = True
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			provider = providers.Provider.create_provider( self.ds, username='OU' )
		testapp = TestApp( self.app )

		data = json.serialize( { 'Class': 'ClassInfo', 'MimeType': 'application/vnd.nextthought.classinfo',
								 'ContainerId': 'Classes',
								 'ID': 'CS2503',
								 'Sections': [{'ID': 'CS2503.101', 'Class': 'SectionInfo', 'Enrolled': ['jason.madden@nextthought.com']}]} )
		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )


		body = json.loads( res.body )
		assert_that( body, has_entry( 'ID', 'CS2503' ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
		assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
		if get:
			res = testapp.get( path + 'Classes/CS2503', extra_environ=self._make_extra_environ() )
			body = json.loads( res.body )
			assert_that( body, has_entry( 'ID', 'CS2503' ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'ID', 'CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'NTIID', 'tag:nextthought.com,2011-10:OU-MeetingRoom:ClassSection-CS2503.101' ) ) ) )
			assert_that( body, has_entry( 'Sections', has_item( has_entry( 'Enrolled', has_item( 'jason.madden@nextthought.com' ) ) ) ) )


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
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/SimplePersistentEnclosure' ) ) ) )

		res = testapp.get( '/dataserver2/providers/OU/Classes/CS2051/SimplePersistentEnclosure', extra_environ=self._make_extra_environ() )
		assert_that( res.content_type, is_( 'image/png' ) )
		assert_that( res.body, is_( data ) )

		res = testapp.post( path, data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 201 ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/SimplePersistentEnclosure' ) ) ) )
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/SimplePersistentEnclosure-2' ) ) ) )

		path = '/dataserver2/providers/OU/Classes'
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
#		from IPython.core.debugger import Tracer; debug_here = Tracer()()
		links = body['Items']['CS2051']['Links']
		assert_that( links, has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/SimplePersistentEnclosure' ) ) )

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
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/TheSlug' ) ) ) )
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



	def test_quiz_container_id_auto_mapping(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

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
		result_data = {"Class": "QuizResult", "MimeType":"application/vnd.nextthought.quizresult",
					   "ContainerId": container_id,
					   'Items': {"1": "0"}}
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
		assert_that( body, has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug' ) ) ) )

		# Getting just the classes is correct link as well
		res = testapp.get( '/dataserver2/providers/OU/Classes', extra_environ=self._make_extra_environ() )
		body = json.loads( res.body )
		links = body['Items']['CS2051']['Sections'][0]['Links']
		assert_that( links, has_item( has_entry( 'href', '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug' ) ) )

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
		res = testapp.delete( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug', extra_environ=self._make_extra_environ() )
		assert_that( res, has_property( 'status_int', 204 ) )
		# Delete it
		#res = testapp.delete( path, extra_environ=self._make_extra_environ() )
		#assert_that( res, has_property( 'status_int', 204 ) )


		testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug',
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


		testapp.get( '/dataserver2/providers/OU/Classes/CS2051/CS2051.101/TheSlug',
					 extra_environ=self._make_extra_environ(),
					 status=404	)

	def test_share_note_with_class(self):
		"We can share with the NTIID of a class we are enrolled in to get to the other students and instructors."
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )

			klass = _create_class( self.ds, ('sjohnson@nextthought.com','jason.madden@nextthought.com') )
			sect = list(klass.Sections)[0]
			sect_ntiid = sect.NTIID
			sect.InstructorInfo.Instructors.append( 'foo@bar' )

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = 'tag:nti:foo'
			user.addContainedObject( n )
			assert_that( n.sharingTargets, is_( set() ) )

		testapp = TestApp( self.app )
		data = '["' + sect_ntiid + '"]'

		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % datastructures.to_external_ntiid_oid( n )
		field_path = path + '/sharedWith' # The name of the external field

		res = testapp.put( urllib.quote( field_path ),
						   data,
						   extra_environ=self._make_extra_environ(),
						   headers={"Content-Type": "application/json" } )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'sharedWith', ['foo@bar', 'jason.madden@nextthought.com'] ) )

	def test_user_search_returns_enrolled_classes(self):
		"We can find class sections we are enrolled in with a search"
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			self._create_user( username='jason.madden@nextthought.com' )

			klass = _create_class( self.ds, ('sjohnson@nextthought.com','jason.madden@nextthought.com') )
			sect = list(klass.Sections)[0]
			sect_name = sect.ID
			sect_ntiid = sect.NTIID

		testapp = TestApp( self.app )

		path = '/dataserver2/UserSearch/' + sect_name

		res = testapp.get( urllib.quote( path ),
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.json_body, has_entry( 'Items', has_item( has_entry( 'Class', 'SectionInfo' ) ) ) )
		sect_info = res.json_body['Items'][0]

		assert_that( sect_info, has_entry( 'Username', sect_ntiid ) )
		assert_that( sect_info, has_entry( 'alias', sect_name ) )
		assert_that( sect_info, has_key( 'avatarURL' ) )




def _create_class(ds, usernames_to_enroll=()):
	provider = providers.Provider.create_provider( ds, username='OU' )
	klass = provider.maybeCreateContainedObjectWithType(  'Classes', None )
	klass.containerId = 'Classes'
	klass.ID = 'CS2051'
	klass.Description = 'CS Class'
	mock_dataserver.current_transaction.add( klass )
	#with mock_dataserver.mock_db_trans(ds) as txn:
	#	txn.add( klass )

	section = classes.SectionInfo()
	section.ID = 'CS2051.101'
	section.creator = provider
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

class TestApplicationLibraryBase(ApplicationTestBase):
	_check_content_link = True
	_stream_type = 'Stream'
	child_ntiid = ntiids.make_ntiid( provider='ou', specific='test2', nttype='HTML' )

	def _setup_library(self, content_root='/prealgebra/', lastModified=None):
		test_self = self
		class NID(object):
			interface.implements( lib_interfaces.IContentUnit )
			ntiid = test_self.child_ntiid
			href = 'sect_0002.html'
			__parent__ = None
			__name__ = 'The name'
			def with_parent( self, p ):
				self.__parent__ = p
				return self

		class LibEnt(object):
			interface.implements( lib_interfaces.IContentPackage )
			root = content_root
			ntiid = None
			__parent__ = None


		if lastModified is not None:
			NID.lastModified = lastModified
			LibEnt.lastModified = lastModified

		class Lib(object):
			interface.implements( lib_interfaces.IContentPackageLibrary )
			titles = ()

			def __getitem__(self, key):
				if key != test_self.child_ntiid:
					raise KeyError( key )
				return NID().with_parent( LibEnt() )

			def pathToNTIID( self, ntiid ):
				return [NID().with_parent( LibEnt() )] if ntiid == test_self.child_ntiid else None

		return Lib()


	def test_library_accept_json(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		for accept_type in ('application/json','application/vnd.nextthought.pageinfo','application/vnd.nextthought.pageinfo+json'):

			res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
							   headers={"Accept": accept_type},
							   extra_environ=self._make_extra_environ() )
			assert_that( res.status_int, is_( 200 ) )

			assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
			assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
			if self._check_content_link:
				assert_that( res.json_body, has_entry( 'Links', has_item( all_of( has_entry( 'rel', 'content' ),
																				  has_entry( 'href', '/prealgebra/sect_0002.html' ) ) ) ) )

			assert_that( res.json_body, has_entry( 'Links', has_item( all_of( has_entry( 'rel', self._stream_type ),
																			  has_entry( 'href',
																						 urllib.quote(
																						 '/dataserver2/users/sjohnson@nextthought.com/Pages(' + self.child_ntiid + ')/' + self._stream_type ) ) ) ) ) )


class TestApplicationLibrary(TestApplicationLibraryBase):


	def test_library_redirect(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )
		# Unauth gets nothing
		testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, status=401 )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 303 ) )
		assert_that( res.headers, has_entry( 'Location', 'http://localhost/prealgebra/sect_0002.html' ) )


	def test_library_redirect_with_fragment(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp( self.app )


		fragment = "#fragment"
		ntiid = self.child_ntiid + fragment
		res = testapp.get( '/dataserver2/NTIIDs/' + ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 303 ) )
		assert_that( res.headers, has_entry( 'Location', 'http://localhost/prealgebra/sect_0002.html' ) )


	def test_library_accept_link(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={"Accept": "application/vnd.nextthought.link+json"},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.link+json' ) )
		assert_that( res.json_body, has_entry( 'href', '/prealgebra/sect_0002.html' ) )


	def test_directly_set_page_shared_settings(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			# First, we must put an object so we have a container
			note = contenttypes.Note()
			note.containerId = self.child_ntiid
			user.addContainedObject( note )

		# Ensure we have modification dates on our _NTIIDEntries
		# so that our trump behaviour works as expected
		self.config.registry.registerUtility( self._setup_library(lastModified=1000) )
		accept_type = 'application/json'
		testapp = TestApp( self.app )
		# To start with, there is no modification info
		res = testapp.get( str('/dataserver2/NTIIDs/' + self.child_ntiid),
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( 1000, webob.datetime_utils.UTC ) ) )


		data = json.dumps( {"sharedWith": ["a@b"] } )
		now = datetime.datetime.now(webob.datetime_utils.UTC)
		now = now.replace( microsecond=0 )

		res = testapp.put( str('/dataserver2/NTIIDs/' + self.child_ntiid + '/++fields++sharingPreference'),
						   data,
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )

		# Now there is modification
		assert_that( res.last_modified, is_( greater_than_or_equal_to( now ) ) )
		last_mod = res.last_modified
		# And it is maintained
		res = testapp.get( str('/dataserver2/NTIIDs/' + self.child_ntiid),
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.last_modified, is_( last_mod ) )




class TestApplicationLibraryNoSlash(TestApplicationLibrary):

	def _setup_library(self, *args, **kwargs):
		return super(TestApplicationLibraryNoSlash,self)._setup_library( content_root="prealgebra", **kwargs )

class TestRootPageEntryLibrary(TestApplicationLibraryBase):
	child_ntiid = ntiids.ROOT
	_check_content_link = False
	_stream_type = 'RecursiveStream'

	def test_set_root_page_prefs_inherits(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		testapp = TestApp( self.app )

		# First, put to the root
		now = datetime.datetime.now(webob.datetime_utils.UTC)
		now = now.replace( microsecond=0 )

		accept_type = 'application/json'
		data = json.dumps( {"sharedWith": ["a@b"] } )

		res = testapp.put( str('/dataserver2/NTIIDs/' + ntiids.ROOT + '/++fields++sharingPreference'),
						   data,
						   headers={"Accept": accept_type},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )

		# Then, reset the library so we have a child, and get the child
		self.child_ntiid = TestApplicationLibrary.child_ntiid
		self.config.registry.registerUtility( self._setup_library() )

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={"Accept": accept_type },
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
		assert_that( res.json_body, has_entry( 'sharingPreference', has_entry( 'sharedWith', ['a@b'] ) ) )
		# Now there is modification
		assert_that( res.last_modified, is_( greater_than_or_equal_to( now ) ) )


from nti.contentlibrary.filesystem import DynamicLibrary as FileLibrary
from nti.assessment import interfaces as asm_interfaces, parts as asm_parts, question as asm_question, submission as asm_submission
from nti.tests import verifiably_provides
from nti.appserver import interfaces as app_interfaces
from hamcrest import has_key
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields

class TestApplicationAssessment(ApplicationTestBase):
	child_ntiid =  'tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.1'

	def _setup_library( self, *args, **kwargs ):
		return FileLibrary( os.path.join( os.path.dirname(__file__), 'ExLibrary' ) )

	def test_registered_utility(self):
		qmap = component.getUtility( asm_interfaces.IQuestionMap )
		assert_that( qmap,
					 verifiably_provides( app_interfaces.IFileQuestionMap ) )
		assert_that( qmap,
					 has_length( 25 ) )
		assert_that( qmap,
					 has_key( self.child_ntiid ) )
		assert_that( qmap.by_file,
					 has_key( os.path.join( os.path.dirname(__file__), 'ExLibrary', 'WithAssessment', 'tag_nextthought.com,2011-10_mathcounts-HTML-MN.2012.0.html' ) ) )



	def test_fetch_assessment_question(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )
		# These inherit the same ACLs as the content they came with
		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, status=401 )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Class', 'Question' ) )

	def test_fetch_pageinfo_with_questions(self):

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		for accept_type in ('application/json','application/vnd.nextthought.pageinfo','application/vnd.nextthought.pageinfo+json'):

			res = testapp.get( '/dataserver2/NTIIDs/tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0',
							   headers={"Accept": accept_type},
							   extra_environ=self._make_extra_environ() )
			assert_that( res.status_int, is_( 200 ) )
			assert_that( res.last_modified, is_( not_none() ) )

			assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
			assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
			assert_that( res.json_body, has_entry( 'AssessmentItems', has_item( has_entry( 'NTIID', self.child_ntiid ) ) ) )
			assert_that( res.json_body, has_entry( 'Last Modified', greater_than( 0 ) ) )

	def test_posting_assesses(self):

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		sub = asm_submission.QuestionSubmission( questionId=self.child_ntiid, parts=('correct',) )
		ext_obj = toExternalObject( sub )
		ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'
		data = json.serialize( ext_obj )
		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )

		assert_that( res.json_body, has_entry( StandardExternalFields.CLASS, 'AssessedQuestion' ) )
		assert_that( res.json_body, has_entry( StandardExternalFields.CREATED_TIME, is_( float ) ) )
		assert_that( res.json_body, has_entry( StandardExternalFields.LAST_MODIFIED, is_( float ) ) )
		assert_that( res.json_body, has_entry( StandardExternalFields.MIMETYPE, 'application/vnd.nextthought.assessment.assessedquestion' ) )
