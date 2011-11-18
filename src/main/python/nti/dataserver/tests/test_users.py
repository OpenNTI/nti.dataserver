#!/usr/bin/env python2.7

from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance, is_not, none)
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

from ..users import User, FriendsList, Device
from ..interfaces import IFriendsList
from ..contenttypes import Note
from ..activitystream_change import Change
from . import provides
from mock_dataserver import WithMockDSTrans
import persistent.wref

class TestUser(unittest.TestCase):

	def test_create_friends_list_through_registry(self):

		user = User( 'foo@bar', 'temp' )
		created = user.maybeCreateContainedObjectWithType( 'FriendsLists', {'Username': 'Friend' } )
		assert_that( created, is_(FriendsList) )
		assert_that( created.username, is_( 'Friend' ) )
		assert_that( created, provides( IFriendsList ) )

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

if __name__ == '__main__':
	unittest.main()
