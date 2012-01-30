#!/usr/bin/env python2.7

from hamcrest import (assert_that, is_, has_entry, instance_of,
					  is_in, not_none, is_not, greater_than_or_equal_to,
					  has_value,
					  same_instance, is_not, none, has_length, has_item,
					  contains)
import unittest

import UserDict
import collections

import persistent
import json
import plistlib
from nti.dataserver.datastructures import (getPersistentState, toExternalOID, toExternalObject,
									   ExternalizableDictionaryMixin, CaseInsensitiveModDateTrackingOOBTree,
									   LastModifiedCopyingUserList, PersistentExternalizableWeakList,
									   ContainedStorage, ContainedMixin, CreatedModDateTrackingObject,
									   to_external_representation, EXT_FORMAT_JSON, EXT_FORMAT_PLIST)

from ..users import User, FriendsList, Device, Community
from ..interfaces import IFriendsList
from ..contenttypes import Note
from ..activitystream_change import Change
from . import provides
import mock_dataserver
from mock_dataserver import WithMockDSTrans
import persistent.wref
import persistent
import mock_dataserver
from nti.dataserver import datastructures
import time

def test_create_friends_list_through_registry():
	def _test( name ):
		user = User( 'foo@bar', 'temp' )
		created = user.maybeCreateContainedObjectWithType( name, {'Username': 'Friend' } )
		assert_that( created, is_(FriendsList) )
		assert_that( created.username, is_( 'Friend' ) )
		assert_that( created, provides( IFriendsList ) )

	yield _test, 'FriendsLists'
	# case insensitive
	yield _test, 'friendslists'

def test_friendslist_updated_through_user_updates_last_mod():
	user = User( 'foo@bar', 'temp' )
	fl = user.maybeCreateContainedObjectWithType( 'FriendsLists', {'Username': 'Friend' } )
	user.addContainedObject( fl )
	fl.lastModified = 0
	now = time.time()

	with user.updates():
		fl2 = user.getContainedObject( fl.containerId, fl.id )
		fl2.updateFromExternalObject( {'friends': []} )

	assert_that( fl.lastModified, is_( greater_than_or_equal_to( now ) ) )
	assert_that( user.getContainer( fl.containerId ).lastModified, is_( greater_than_or_equal_to( now ) ) )

class TestUser(mock_dataserver.ConfiguringTestBase):


	def test_create_device_through_registry(self):
		user = User( 'foo@bar', 'temp' )

		created = user.maybeCreateContainedObjectWithType( 'Devices', 'deadbeef' )
		assert_that( created, is_( Device ) )
		assert_that( created.id, is_( 'deadbeef' ) )
		assert_that( created.deviceId, is_( 'deadbeef'.decode( 'hex' ) ) )
		assert_that( created.containerId, is_( 'Devices' ) )
		assert_that( created.toExternalObject(), is_( 'deadbeef' ) )
		assert_that( created, is_( created ) )

		user.addContainedObject( created )
		assert_that( user.getContainedObject( created.containerId, created.id ),
					 is_( created ) )

	@WithMockDSTrans
	def test_share_unshare_note(self):
		user1 = User( 'foo@bar', 'temp' )
		user2 = User( 'fab@bar', 'temp' )

		note = Note()
		note['body'] = ['text']
		note.containerId = 'c1'
		note.creator = user1.username

		user1.addContainedObject( note )
		assert_that( note.id, is_not( none() ) )

		note.addSharingTarget( 'fab@bar', actor=user1 )
		note.id = 'foobar' # to ensure it doesn't get used or changed by the sharing process
		user2._noticeChange( Change( Change.SHARED, note ) )
		assert_that( note.id, is_( 'foobar' ) )
		assert_that( persistent.wref.WeakRef( note ), is_in( user2.getSharedContainer( 'c1' ) ) )

		user2._noticeChange( Change( Change.DELETED, note ) )
		assert_that( persistent.wref.WeakRef( note ), is_not( is_in( user2.getSharedContainer( 'c1' ) ) ) )
		assert_that( note.id, is_( 'foobar' ) )

	@mock_dataserver.WithMockDS
	def test_share_note_with_updates(self):
		with mock_dataserver.current_mock_ds.dbTrans():
			user1 = User.create_user( mock_dataserver.current_mock_ds, username='foo@bar' )
			user2 = User.create_user( mock_dataserver.current_mock_ds, username='fab@bar' )

			note = Note()
			note['body'] = ['text']
			note.containerId = 'c1'
			note.creator = user1.username

			user1.addContainedObject( note )
			assert_that( note.id, is_not( none() ) )

		with mock_dataserver.current_mock_ds.dbTrans():
			user1 = User.get_user( 'foo@bar', dataserver=mock_dataserver.current_mock_ds )
			nots = []
			user1._postNotification = lambda *args: nots.extend( args )
			lm = None
			with user1.updates():
				c_note = user1.getContainedObject( note.containerId, note.id )
				assert_that( c_note, is_( same_instance( user1._v_updateSet[0][0] ) ) )
				c_note.addSharingTarget( User.get_user( 'fab@bar', dataserver=mock_dataserver.current_mock_ds ),
										 actor=user1 )
				assert_that( c_note.getFlattenedSharingTargetNames(), is_( set(['fab@bar']) ) )
				assert_that( datastructures.getPersistentState( c_note ), is_( persistent.CHANGED ) )
				lm = c_note.lastModified
			del user1._postNotification
			assert_that( user1.containers['c1'].lastModified, is_( greater_than_or_equal_to( lm ) ) )
			assert_that( user1.containers['c1'].lastModified, is_( user1.containers['c1'][note.id].lastModified ) )
			assert_that( nots, is_( ['Modified', (c_note, set())] ) )

	@mock_dataserver.WithMockDS
	def test_delete_shared_note_notifications(self):
		with mock_dataserver.current_mock_ds.dbTrans():
			user1 = User.create_user( mock_dataserver.current_mock_ds, username='foo@bar' )
			user2 = User.create_user( mock_dataserver.current_mock_ds, username='fab@bar' )

			note = Note()
			note['body'] = ['text']
			note.containerId = 'c1'
			note.creator = user1.username

			user1.addContainedObject( note )
			assert_that( note.id, is_not( none() ) )

			note.addSharingTarget( user2, actor=user1 )

		with mock_dataserver.current_mock_ds.dbTrans():
			user1 = User.get_user( 'foo@bar', dataserver=mock_dataserver.current_mock_ds )
			nots = []
			user1._postNotification = lambda *args: nots.append( args )
			lm = None
			with user1.updates():
				c_note = user1.getContainedObject( note.containerId, note.id )
				assert_that( c_note, is_( same_instance( user1._v_updateSet[0][0] ) ) )
				user1.deleteContainedObject( c_note.containerId, c_note.id )
				assert_that( datastructures.getPersistentState( c_note ), is_( persistent.CHANGED ) )

			del user1._postNotification

			# No modified notices, just the Deleted notice.
			assert_that( nots, is_( [('Deleted', c_note)] ) )

	@WithMockDSTrans
	def test_getSharedContainer_defaults( self ):
		user = User( 'sjohnson@nextthought.com', 'temp001' )
		assert_that( user.getSharedContainer( 'foo', 42 ), is_( 42 ) )

		c = ContainedMixin()
		c.containerId = 'foo'
		c.id = 'a'

		user._addSharedObject( c )
		assert_that( user.getSharedContainer( 'foo' ), has_length( 1 ) )

		# Deleting it, we get back the now-empty container, not the default
		# value
		user._removeSharedObject( c )
		assert_that( user.getSharedContainer( 'foo', 42 ), has_length( 0 ) )

	@WithMockDSTrans
	def test_getContainedStream_Note_shared_community_cache(self):
		"We should be able to get the contained stream if there are things shared with a community in the cache"
		user = User.create_user( self.ds, username='sjohnson@nextthought.com', password='temp001' )
		user2 = User.create_user( self.ds, username='jason@nextthought.com', password='temp001' )
		comm = Community( 'AoPS' )
		self.ds.root['users'][comm.username] = comm

		user.join_community( comm ); user2.join_community( comm )
		user.follow( comm )

		note = Note()
		note.containerId = 'foo'
		note.addSharingTarget( comm )
		user2.addContainedObject( note )
		# What really gets shared in the returned value,
		# which may be (is) wrapped in a ContainedProxy
		note = user2.getContainedObject( 'foo', note.id )

		change = Change( Change.SHARED, note )
		change.creator = 42
		comm._noticeChange( change )

		assert_that( user.getContainedStream('foo'), contains( change ) )
		# This way we're sure it's the one we have above
		assert_that( user.getContainedStream('foo')[0].creator, is_( 42 ) )

	@WithMockDSTrans
	def test_getContainedStream_Note_shared_community_nocache(self):
		"We should be able to get the contained stream if there are things shared with a community not in the cache"
		user = User.create_user( self.ds, username='sjohnson@nextthought.com', password='temp001' )
		user2 = User.create_user( self.ds, username='jason@nextthought.com', password='temp001' )
		comm = Community( 'AoPS' )
		self.ds.root['users'][comm.username] = comm

		user.join_community( comm ); user2.join_community( comm )
		user.follow( comm )

		note = Note()
		note.containerId = 'foo'
		note.addSharingTarget( comm )
		user2.addContainedObject( note )
		# What really gets shared in the returned value,
		# which may be (is) wrapped in a ContainedProxy
		note = user2.getContainedObject( 'foo', note.id )

		change = Change( Change.SHARED, note )
		change.creator = 42
		comm._noticeChange( change )
		del comm.streamCache.get( 'foo' )[:]

		assert_that( user.getContainedStream('foo'), is_not( contains( change ) ) )
		# This one is synthesized
		assert_that( user.getContainedStream('foo')[0].creator, is_( user2 ) )
		assert_that( user.getContainedStream('foo')[0].object, is_( note ) )

from zope.component import eventtesting
from zope.event import notify
from nti.apns import APNSDeviceFeedback

class TestFeedbackEvent(mock_dataserver.ConfiguringTestBase):

	def setUp(self):
		super(TestFeedbackEvent,self).setUp()
		eventtesting.clearEvents()


	@WithMockDSTrans
	def test_devicefeedback(self):
		user = User.create_user( self.ds, username='sjohnson@nextthought.com', password='temp001' )
		device = user.maybeCreateContainedObjectWithType( 'Devices', 'deadbeef' )
		user.addContainedObject( device )
		assert_that( user.devices, has_value( device ) )
		assert_that( user.devices, has_length( 2 ) ) # Last Modified, Device

		event = APNSDeviceFeedback( 5, 'deadbeef'.decode('hex') )
		notify( event )

		assert_that( user.devices, has_length( 1 ) )

if __name__ == '__main__':
	unittest.main()
