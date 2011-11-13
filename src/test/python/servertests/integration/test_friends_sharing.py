import uuid

from servertests.contenttypes import Note
from servertests.contenttypes import FriendsList
from servertests import DataServerTestCase

from servertests.integration import has_same_oid_as
from servertests.integration import shared_with
from servertests.integration import contained_in
from servertests.integration import containing_friends
from servertests.integration import container_of_length

from hamcrest import is_
from hamcrest import assert_that

class TestFriendsSharing(DataServerTestCase):

	OWNER = ('test.user.1@nextthought.com', 'temp001')
	FRIENDS = [('test.user.%s@nextthought.com' % r, 'temp001') for r in xrange(2,4)]
	NOTE = 'A note to share'

	def setUp(self):
		super(TestFriendsSharing, self).setUp()
		self.ds.setCredentials(self.OWNER)
		self.CONTAINER = 'container-%s' % uuid.uuid1()
		self.LIST_NAME = 'friends-%s' % uuid.uuid1()

	def _create_friend_list(self, client, name, friends):
		fl = FriendsList(name=name, friends=friends)
		return client.createFriendsList(fl)

	def _create_friends_fake_notes(self):
		objects =[]
		for f in self.FRIENDS:
			username = f[0]
			container = str(uuid.uuid1())
			note = Note(text='Fake note owned by %s' % username, container=container)
			self.ds.clearCredentials()
			self.ds.setCredentials(f)
			objects.append(self.ds.createObject(note, adapt=True))
		return objects

	def _delete_friends_fake_notes(self, objects):
		it = iter(objects)
		for f in self.FRIENDS:
			self.ds.clearCredentials()
			self.ds.setCredentials(f)
			self.ds.deleteObject(it.next())

	def _check_object_in_friends(self, createdObj, container, friends):
		for f in friends:
			self.ds.clearCredentials()
			self.ds.setCredentials(f)
			user_data = self.ds.getUserGeneratedData(container)
			assert_that(createdObj, contained_in(user_data))

	def test_share_with_friends(self):

		objects = self._create_friends_fake_notes()

		# restore credentials
		self.ds.setCredentials(self.OWNER)

		# create friends list
		friends = [r[0] for r in self.FRIENDS]
		friendsList = self._create_friend_list(self.ds, self.LIST_NAME, friends)
		self.assertTrue(friendsList is not None)

		# create an object to share
		note = Note(text=self.NOTE, container=self.CONTAINER)
		createdObj = self.ds.createObject(note, adapt=True)
		self.assertTrue(createdObj is not None)

		# do the actual sharing
		createdObj.shareWith( self.LIST_NAME )
		sharedObj = self.ds.updateObject(createdObj)
		self.assertTrue(sharedObj is not None)

		assert_that(sharedObj, has_same_oid_as(createdObj))
		assert_that(sharedObj, shared_with(friends))

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that the friends can now see it
		self._check_object_in_friends(createdObj, self.CONTAINER, self.FRIENDS)

		# clean up
		self.ds.setCredentials(self.OWNER)
		self.ds.deleteObject(friendsList)
		self.ds.deleteObject(createdObj)

		self._delete_friends_fake_notes(objects)

	def test_share_with_friends_and_remove_friend(self):
		"""
		removing a friend from the friend list does not have
		any effect w: the sharing
		"""

		objects = self._create_friends_fake_notes()
		self.ds.setCredentials(self.OWNER)

		# create friends list
		friends = [r[0] for r in self.FRIENDS]
		friendsList = self._create_friend_list(self.ds, self.LIST_NAME, friends)

		# create and share
		note = Note(text=self.NOTE, container=self.CONTAINER)
		note.shareWith(  friends )
		createdObj = self.ds.createObject(note, adapt=True)
		assert_that(createdObj, shared_with(friends))

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent(maxWaitSeconds=7)

		# check that the friends can now see it
		self._check_object_in_friends(createdObj, self.CONTAINER, self.FRIENDS)
		self.ds.setCredentials(self.OWNER)

		# update friend list
		friends.pop()
		friendsList['friends'] = friends
		friendsList = self.ds.updateObject(friendsList, oid=friendsList.id)
		assert_that(friendsList, is_(containing_friends(friends)))

		# check still I shared still can see the object
		self._check_object_in_friends(createdObj, self.CONTAINER, self.FRIENDS)

		# clean up
		self.ds.setCredentials(self.OWNER)
		self.ds.deleteObject(friendsList)
		self.ds.deleteObject(createdObj)

		self._delete_friends_fake_notes(objects)

	def test_share_with_friends_and_delete_obj(self):

		objects = self._create_friends_fake_notes()
		self.ds.setCredentials(self.OWNER)

		# create friends list
		friends = [r[0] for r in self.FRIENDS]
		friendsList = self._create_friend_list(self.ds, self.LIST_NAME, friends)

		# create and share
		note = Note(text=self.NOTE, container=self.CONTAINER)
		note.shareWith( friends )
		createdObj = self.ds.createObject(note, adapt=True)
		assert_that(createdObj, shared_with(friends))

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent(maxWaitSeconds=7)

		# check that the friends can now see it
		self._check_object_in_friends(createdObj, self.CONTAINER, self.FRIENDS)
		self.ds.setCredentials(self.OWNER)

		# remove object
		self.ds.deleteObject(createdObj)

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		for f in self.FRIENDS:
			self.ds.clearCredentials()
			self.ds.setCredentials(f)
			user_data = self.ds.getUserGeneratedData(self.CONTAINER)
			assert_that(user_data, container_of_length(0))

		# clean up
		self.ds.setCredentials(self.OWNER)
		self.ds.deleteObject(friendsList)

		self._delete_friends_fake_notes(objects)

if __name__ == '__main__':
	import unittest
	unittest.main()

