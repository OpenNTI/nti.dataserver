#!/usr/bin/env python2.7

from hamcrest import (assert_that, is_, has_entry, instance_of,
					  has_key, is_in, not_none, is_not, greater_than,
					  same_instance)
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

from ..users import User, FriendsList
from ..interfaces import IFriendsList
from . import provides

class TestUser(unittest.TestCase):

	def test_create_friends_list_through_registry(self):

		user = User( 'foo@bar', 'temp' )
		created = user.maybeCreateContainedObjectWithType( 'FriendsLists', {'Username': 'Friend' } )
		assert_that( created, is_(FriendsList) )
		assert_that( created.username, is_( 'Friend' ) )
		assert_that( created, provides( IFriendsList ) )

if __name__ == '__main__':
	unittest.main()
