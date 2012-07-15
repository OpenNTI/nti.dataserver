#!/usr/bin/env python2.7

from hamcrest import (assert_that, is_, has_entry, instance_of,
					  is_in, not_none, is_not, greater_than_or_equal_to,
					  has_value, has_property,
					  same_instance, is_not, none, has_length,
					  contains)
import unittest
from nose.tools import assert_raises


import persistent

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization import internalization

from nti.dataserver.datastructures import  ZContainedMixin as ContainedMixin
from nti.dataserver.users import User, FriendsList, Device, Community, _FriendsListMap as FriendsListContainer
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.contenttypes import Note
from nti.dataserver.activitystream_change import Change
from . import provides

from nti.externalization.persistence import getPersistentState

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from zope.container.interfaces import InvalidItemType

import mock_dataserver
from mock_dataserver import WithMockDSTrans
import persistent.wref
from nti.dataserver import datastructures
import time

class PersistentContainedThreadable(ContainedMixin,persistent.Persistent):
	lastModified = 0
	inReplyTo = None
	creator = None
	references = ()
	shared_with = True
	def isSharedWith( self, other ):
		return self.shared_with

	def __repr__(self):
		return repr( (self.__class__.__name__, self.containerId, self.id) )

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

def test_adding_wrong_type_to_friendslist():
	friends = FriendsListContainer()
	with assert_raises(InvalidItemType):
		friends['k'] = 'v'

def test_friends_list_case_insensitive():
	user = User( 'foo@bar', 'temp' )
	fl = user.maybeCreateContainedObjectWithType( 'FriendsLists', {'Username': 'Friend' } )
	user.addContainedObject( fl )

	assert_that( user.getContainedObject( "FriendsLists", "Friend" ),
				 is_( user.getContainedObject( 'FriendsLists', "friend" ) ) )


def test_everyone_has_creator():
	assert_that( users.EVERYONE, has_property( 'creator', nti_interfaces.SYSTEM_USER_NAME ) )


class TestUser(mock_dataserver.ConfiguringTestBase):


	def test_friendslist_updated_through_user_updates_last_mod(self):
		user = User( 'foo@bar', 'temp' )
		fl = user.maybeCreateContainedObjectWithType( 'FriendsLists', {'Username': 'Friend' } )
		user.addContainedObject( fl )
		fl.lastModified = 0
		now = time.time()

		with user.updates():
			fl2 = user.getContainedObject( fl.containerId, fl.id )
			internalization.update_from_external_object( fl2, {'friends': []} )

		assert_that( fl.lastModified, is_( greater_than_or_equal_to( now ) ) )
		assert_that( user.getContainer( fl.containerId ).lastModified, is_( greater_than_or_equal_to( now ) ) )


	def test_create_device_through_registry(self):
		user = User( 'foo@bar', 'temp' )

		created = user.maybeCreateContainedObjectWithType( 'Devices', 'deadbeef' )
		assert_that( created, is_( Device ) )
		assert_that( created.id, is_( 'deadbeef' ) )
		assert_that( created.deviceId, is_( 'deadbeef'.decode( 'hex' ) ) )
		assert_that( created.containerId, is_( 'Devices' ) )
		assert_that( created.toExternalObject(), has_entry( 'ID', 'deadbeef' ) )
		assert_that( created, is_( created ) )

		user.addContainedObject( created )
		assert_that( user.getContainedObject( created.containerId, created.id ),
					 is_( created ) )

	def test_clear_notification_count(self):
		user = User( 'foo@bar', 'temp' )
		user.lastLoginTime.value = 1
		user.notificationCount.value = 5

		user.updateFromExternalObject( {'lastLoginTime': 2} )
		assert_that( user.lastLoginTime, has_property( 'value', 2 ) )
		assert_that( user.notificationCount, has_property( 'value', 0 ) )

		user.lastLoginTime.value = 1
		user.notificationCount.value = 5
		user.updateFromExternalObject( {'NotificationCount': 2} )
		assert_that( user.lastLoginTime, has_property( 'value', 1 ) )
		assert_that( user.notificationCount, has_property( 'value', 2 ) )


	@WithMockDSTrans
	def test_share_unshare_note(self):
		user1 = User.create_user( self.ds, username='foo@bar', password='temp' )
		user2 = User.create_user( self.ds, username='fab@bar', password='temp' )

		note = Note()
		note.body = ['text']
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
		with mock_dataserver.mock_db_trans():
			user1 = User.create_user( mock_dataserver.current_mock_ds, username='foo@bar' )
			user2 = User.create_user( mock_dataserver.current_mock_ds, username='fab@bar' )

			note = Note()
			note.body = ['text']
			note.containerId = 'c1'
			note.creator = user1.username

			user1.addContainedObject( note )
			assert_that( note.id, is_not( none() ) )

		with mock_dataserver.mock_db_trans():
			user1 = User.get_user( 'foo@bar', dataserver=mock_dataserver.current_mock_ds )
			nots = []
			user1._postNotification = lambda *args: nots.extend( args )
			lm = None
			with user1.updates():
				c_note = user1.getContainedObject( note.containerId, note.id )
				assert_that( c_note, is_( same_instance( user1._v_updateSet[0][0] ) ) )
				c_note.addSharingTarget( User.get_user( 'fab@bar', dataserver=mock_dataserver.current_mock_ds ),
										 actor=user1 )
				assert_that( list(c_note.flattenedSharingTargetNames), is_( ['fab@bar'] ) )
				assert_that( getPersistentState( c_note ), is_( persistent.CHANGED ) )
				lm = c_note.lastModified
			del user1._postNotification
			assert_that( user1.containers['c1'].lastModified, is_( greater_than_or_equal_to( lm ) ) )
			assert_that( user1.containers['c1'].lastModified, is_( greater_than_or_equal_to( user1.containers['c1'][note.id].lastModified ) ) )
			assert_that( nots, is_( ['Modified', (c_note, set())] ) )

	@mock_dataserver.WithMockDS
	def test_delete_shared_note_notifications(self):
		with mock_dataserver.mock_db_trans():
			user1 = User.create_user( mock_dataserver.current_mock_ds, username='foo@bar' )
			user2 = User.create_user( mock_dataserver.current_mock_ds, username='fab@bar' )

			note = Note()
			note.body = ['text']
			note.containerId = 'c1'
			note.creator = user1.username

			user1.addContainedObject( note )
			assert_that( note.id, is_not( none() ) )

			note.addSharingTarget( user2, actor=user1 )

		with mock_dataserver.mock_db_trans():
			user1 = User.get_user( 'foo@bar', dataserver=mock_dataserver.current_mock_ds )
			nots = []
			user1._postNotification = lambda *args: nots.append( args )
			lm = None
			with user1.updates():
				c_note = user1.getContainedObject( note.containerId, note.id )
				assert_that( c_note, is_( same_instance( user1._v_updateSet[0][0] ) ) )
				user1.deleteContainedObject( c_note.containerId, c_note.id )
				assert_that( getPersistentState( c_note ), is_( persistent.CHANGED ) )

			del user1._postNotification

			# No modified notices, just the Deleted notice.
			assert_that( nots, is_( [('Deleted', c_note)] ) )

	@WithMockDSTrans
	def test_getSharedContainer_defaults( self ):
		user = User.create_user( self.ds, username='sjohnson@nextthought.com', password='temp001' )
		assert_that( user.getSharedContainer( 'foo', 42 ), is_( 42 ) )

		c = ContainedMixin()
		c.containerId = 'foo'
		c.id = 'a'

		user._addSharedObject( c )
		assert_that( user.getSharedContainer( 'foo' ), has_length( 1 ) )

		# Deleting it, we get back the now-empty container, not the default
		# value
		user._removeSharedObject( c )
		assert_that( list(user.getSharedContainer( 'foo', 42 )), has_length( 0 ) )

	@WithMockDSTrans
	def test_mute_conversation( self ):
		user = User.create_user( self.ds, username='sjohnson@nextthought.com', password='temp001' )

		c = PersistentContainedThreadable()
		c.containerId = 'foo'
		c.id = 'a'

		change = Change( Change.CREATED, c )
		user._acceptIncomingChange( change )
		assert_that( user.getSharedContainer( 'foo' ), has_length( 1 ) )
		assert_that( user.getContainedStream( 'foo' ), has_length( 1 ) )

		user.mute_conversation( to_external_ntiid_oid( c ) )

		# Now, the shared container is empty
		assert_that( list(user.getSharedContainer( 'foo', 42 )), has_length( 0 ) )
		assert_that( user.getContainedStream( 'foo' ), has_length( 0 ) )

		# Stays empty as we reply
		reply = PersistentContainedThreadable()
		reply.containerId = 'foo'
		reply.id = 'b'
		reply.inReplyTo = c
		change = Change( Change.SHARED, reply )
		user._noticeChange( change )



		assert_that( list(user.getSharedContainer( 'foo', 42 )), has_length( 0 ) )
		assert_that( user.getContainedStream( 'foo' ), has_length( 0 ) )

		# Stays empty as we reference
		reference = PersistentContainedThreadable()
		reference.containerId = 'foo'
		reference.id = '3'
		reference.references = [c]
		change = Change( Change.SHARED, reference )
		user._noticeChange( change )


		assert_that( list(user.getSharedContainer( 'foo', 42 )), has_length( 0 ) )
		assert_that( user.getContainedStream( 'foo' ), has_length( 0 ) )

		# But unmuting it brings all the objects back
		user.unmute_conversation( to_external_ntiid_oid( c ) )
		assert_that( list(user.getSharedContainer( 'foo' )), has_length( 3 ) )
		assert_that( user.getContainedStream( 'foo' ), has_length( 3 ) )

		user.mute_conversation( to_external_ntiid_oid( c ) )
		# and they can all go away
		assert_that( list(user.getSharedContainer( 'foo', 42 )), has_length( 0 ) )
		assert_that( user.getContainedStream( 'foo' ), has_length( 0 ) )
		# If a DELETE arrives while muted, then it is still missing when unmuted
		change = Change( Change.DELETED, reference )
		user._noticeChange( change )

		user.unmute_conversation( to_external_ntiid_oid( c ) )
		assert_that( user.getSharedContainer( 'foo' ), has_length( 2 ) )
		assert_that( user.getContainedStream( 'foo' ), has_length( 2 ) )


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
		assert_that( user.devices, has_length( 1 ) )

		event = APNSDeviceFeedback( 5, 'deadbeef'.decode('hex') )
		notify( event )

		assert_that( user.devices, has_length( 0 ) )

if __name__ == '__main__':
	unittest.main()
