import time

from servertests import DataServerTestCase

from servertests.integration import containing_friend
from servertests.integration import containing_friends
from servertests.integration import containing_no_friends
from servertests.integration import contains_friendslist
from servertests.integration import friendslistFromFriendsLists
from servertests.integration import accepting

from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_key


class TestBasicFriendsLists(DataServerTestCase):

	OWNER = ('test.user.1@nextthought.com', 'temp001')
	FRIEND = ('test.user.3@nextthought.com','temp001')

	def setUp(self):
		super(TestBasicFriendsLists, self).setUp()
		self.ds.setCredentials(self.OWNER)
		self.LIST_NAME='TestFriendsList-%s@nextthought.com' % time.time()

		self.ds.getUserObject(credentials=self.FRIEND)

	def test_has_everyone_by_default(self):
		lists = self.ds.getFriendsLists()
		assert_that(lists, contains_friendslist('Everyone'))

	def test_can_create_empty_friendslist(self):
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.LIST_NAME, [])

		lists = self.ds.getFriendsLists()

		assert_that(lists, contains_friendslist(self.LIST_NAME))

		friendsList = friendslistFromFriendsLists(lists, self.LIST_NAME)

		assert_that(friendsList, is_(containing_no_friends()))

		# cleanup
		self.ds.deleteObject(createdlist)

	def test_can_delete_friendslist(self):
		#TODO: abstract all this object creation away.	Test writers
		#in most cases shouldn't care about the dict structure
		friends = ['test.user.5@nextthought.com', 'tester6@nextthought.com']
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.LIST_NAME, friends)

		lists = self.ds.getFriendsLists()
		assert_that(lists, contains_friendslist(self.LIST_NAME))

		friendsList = friendslistFromFriendsLists(lists, self.LIST_NAME)
		assert_that(friendsList, is_(containing_friends(friends)))

		self.ds.deleteObject(createdlist)
		lists = self.ds.getFriendsLists()
		assert_that(lists, is_not(contains_friendslist(self.LIST_NAME)))

	def test_can_create_friendslist_with_friends(self):
		friends = ['test.user.5@nextthought.com', 'tester6@nextthought.com']
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.LIST_NAME, friends)

		lists = self.ds.getFriendsLists()
		assert_that(lists, contains_friendslist(self.LIST_NAME))

		friendsList = friendslistFromFriendsLists(lists, self.LIST_NAME)
		assert_that(friendsList, is_(containing_friends(friends)))

		# cleanup
		self.ds.deleteObject(createdlist)

	def test_can_delete_from_friendslist(self):
		friends = ['test.user.5@nextthought.com', 'tester6@nextthought.com']
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.LIST_NAME, friends)

		lists = self.ds.getFriendsLists()
		assert_that(lists, contains_friendslist(self.LIST_NAME))

		friendsList = friendslistFromFriendsLists(lists, self.LIST_NAME)
		assert_that(friendsList, is_(containing_friends(friends)))

		updatedFriends = {'friends': [friends[0]]}
		self.ds.updateObject(updatedFriends, oid=friendsList.id)

		lists = self.ds.getFriendsLists()
		assert_that(lists, contains_friendslist(self.LIST_NAME))

		friendsList = friendslistFromFriendsLists(lists, self.LIST_NAME)
		assert_that(friendsList, is_(containing_friend(friends[0])))
		assert_that(friendsList, is_not(containing_friend(friends[1])))

		# cleanup
		self.ds.deleteObject(createdlist)

	#TODO: add test resolved vs. unresolved

	def test_can_add_to_friendslists(self):
		friends = ['test.user.5@nextthought.com', 'tester6@nextthought.com']
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.LIST_NAME, [])

		lists = self.ds.getFriendsLists()
		assert_that(lists, has_key(self.LIST_NAME))

		friendsList = friendslistFromFriendsLists(lists, self.LIST_NAME)
		assert_that(friendsList, is_(containing_no_friends()))

		friendsToAdd = {'friends': [friends[0]]}
		self.ds.updateObject(friendsToAdd, oid=createdlist.id)

		lists = self.ds.getFriendsLists()
		assert_that(lists, is_(contains_friendslist(self.LIST_NAME)))

		friendsList = friendslistFromFriendsLists(lists, self.LIST_NAME)
		assert_that(friendsList, is_(containing_friend(friends[0])))

		friendsToAdd = {'friends': friends}
		self.ds.updateObject(friendsToAdd, oid=createdlist.id)

		lists = self.ds.getFriendsLists()
		assert_that(lists, is_(contains_friendslist(self.LIST_NAME)))

		friendsList = friendslistFromFriendsLists(lists, self.LIST_NAME)
		assert_that(friendsList, is_(containing_friends(friends)))

		# cleanup
		self.ds.deleteObject(createdlist)


	def test_circling_causes_acceptance(self):
		"""
		When a user is circled they are automatically accepting the user that circled them
		"""
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.LIST_NAME, [self.FRIEND[0]])

		self.ds.waitForEvent()

		friendsUserObject = self.ds.getUserObject(credentials=self.FRIEND)

		assert_that(friendsUserObject, is_(accepting(self.OWNER[0])))

		# cleanup
		self.ds.deleteObject(createdlist)

if __name__ == '__main__':
	import unittest
	unittest.main()
