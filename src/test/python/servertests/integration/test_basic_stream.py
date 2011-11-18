import time
import warnings
import urllib2

from servertests import DataServerTestCase
from servertests.integration import container
from servertests.integration import sortchanges
from servertests.integration import of_change_type_circled
from servertests.integration import of_change_type_shared
from servertests.integration import of_change_type_modified
from servertests.integration import objectsFromContainer
from servertests.integration import wraps_item
from servertests.integration import unwrapObject
from servertests.integration import notification_count
from servertests.integration import get_notification_count
from servertests.integration import contains

import unittest
from hamcrest import (assert_that, has_entry, is_, is_not,
					  not_none, greater_than_or_equal_to, has_length)

class TestBasicStream(DataServerTestCase):

	owner = ('test.user.1@nextthought.com', 'temp001')
	target = ('test.user.2@nextthought.com', 'temp001')

# try 50 objects, try 51

	def setUp(self):
		super(TestBasicStream, self).setUp()

		#Changes can't go to users that dont exist so we make sure to autocreate them
		self.ds.getRecursiveStreamData('dontcare', credentials=self.owner)
		self.ds.getRecursiveStreamData('dontcare', credentials=self.target)

		self.CONTAINER = 'TestBasicStream-container-%s' % time.time()
		self.ds.setCredentials(self.owner)

	def test_sharing_goes_to_stream(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0])
		assert_that(sharedObj, not_none())

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that it is in the stream
		stream = self.ds.getRecursiveStreamData(self.CONTAINER, credentials=self.target)
		assert_that(stream, is_(container()))

		sortedchanges = sortchanges(objectsFromContainer(stream))
		assert_that( sortedchanges, has_length( greater_than_or_equal_to( 1 ) ) )
		change = sortedchanges[0]
		assert_that(change, of_change_type_shared())
		assert_that(change, wraps_item(createdObj))

		createdObj2 = self.ds.createNote('A note to share 2', self.CONTAINER)
		self.ds.shareObject(createdObj2, self.target[0])

		createdObj3 =  self.ds.createNote('A note to share 3', self.CONTAINER)
		self.ds.shareObject(createdObj3, self.target[0])

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that it is in the stream
		stream = self.ds.getRecursiveStreamData(self.CONTAINER, credentials=self.target)
		assert_that(stream, is_(container()))

		sortedchanges = sortchanges(objectsFromContainer(stream))
		assert_that(sortedchanges[0], wraps_item(createdObj3))
		assert_that(sortedchanges[0], of_change_type_shared())

		assert_that(sortedchanges[1], wraps_item(createdObj2))
		assert_that(sortedchanges[1], of_change_type_shared())

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdObj2)
		self.ds.deleteObject(createdObj3)

	def test_update_goes_to_stream(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share 3', self.CONTAINER)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0])

		# FIXME: need to abstract this but it requires something more than a plain dict
		# now edit the object.
		updatedText = 'updated text'
		sharedObj['body'] = [updatedText]
		updatedObj = self.ds.updateObject(sharedObj)

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that it is in the stream
		stream = self.ds.getRecursiveStreamData(self.CONTAINER, credentials=self.target)

		# we should have two things. The intial create and then the update	we have another
		# test to verify the create so we only explicitly check for the update
		assert_that( stream, is_(container()) )
		assert_that( stream, has_length( greater_than_or_equal_to( 2 ) ) )

		sortedchanges = sortchanges(objectsFromContainer(stream))
		assert_that( sortedchanges, has_length( greater_than_or_equal_to( 1 ) ) )
		updateChange = sortedchanges[0]
		assert_that(updateChange, of_change_type_modified())
		assert_that(updateChange, wraps_item(updatedObj))
		assert_that(unwrapObject(updateChange), has_entry('text', updatedText))

		# cleanup
		self.ds.deleteObject(createdObj)

	def test_delete_doesnt_goes_to_stream(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share 3', self.CONTAINER)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0])
		assert_that(sharedObj, not_none())

		# now delete it
		self.ds.deleteObject(createdObj)

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that it is in the stream
		stream = self.ds.getRecursiveStreamData(self.CONTAINER, credentials=self.target)

		# things that are deleted don't show up in the stream.  Verify that
		assert_that(stream, is_(container()))

		sortedchanges = sortchanges(objectsFromContainer(stream))
		assert_that( sortedchanges, has_length( greater_than_or_equal_to( 1 ) ) )
		createdChange = sortedchanges[0]
		assert_that(createdChange, of_change_type_shared())
		assert_that(createdChange, wraps_item(createdObj))

	def test_creating_friendslist_goes_to_stream(self):
		# lazy and use the container name
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.CONTAINER, [self.target[0]])

		#We aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		#check that it is in the stream
		stream = self.ds.getRecursiveStreamData(self.CONTAINER, credentials=self.target)

		#Things that are deleted don't show up in the stream.  Verify that
		assert_that(stream, is_(container()))

		sortedchanges = sortchanges(objectsFromContainer(stream))
		assert_that( sortedchanges, has_length( greater_than_or_equal_to( 1 ) ) )
		circledChange = sortedchanges[0]
		assert_that(circledChange, of_change_type_circled())

		# cleanup
		self.ds.deleteObject(createdlist)

	def test_adding_to_friendslist_goes_to_stream(self):
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.CONTAINER, [])

		# FIXME: abstract this away
		updatedFriends = {'friends': [self.target[0]]}

		updatedlist = self.ds.updateObject(updatedFriends, createdlist.id)
		assert_that(updatedlist, not_none())

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		#check that it is in the stream
		stream = self.ds.getRecursiveStreamData(self.CONTAINER, credentials=self.target)

		#Things that are deleted don't show up in the stream.  Verify that
		assert_that(stream, is_(container()))

		sortedchanges = sortchanges(objectsFromContainer(stream))
		assert_that( sortedchanges, has_length( greater_than_or_equal_to( 1 ) ) )
		circledChange = sortedchanges[0]
		assert_that(circledChange, of_change_type_circled())

		# cleanup
		self.ds.deleteObject(createdlist)

	def test_stream_increments_user_notification_count(self):
		targetUserObject = self.ds.getUserObject(credentials=self.target)
		startingCount = get_notification_count(targetUserObject)

		createdObj =  self.ds.createNote('A note to share', self.CONTAINER)
		self.ds.shareObject(createdObj, self.target[0])
		self.ds.waitForEvent()

		targetUserObject = self.ds.getUserObject(credentials=self.target)

		# Notice, however, that because of background processes still finishing,
		# the count may not be exact. It may be higher.
		targetNotificationCount = startingCount + 1
		assert_that(targetUserObject, notification_count(greater_than_or_equal_to(targetNotificationCount)))

		startingCount = get_notification_count(targetUserObject)

		createdObj['text'] = 'junk'
		self.ds.updateObject(createdObj)

		#we want to circle but we have already circled target so we get no notification
		newUser = ('tester-%s@nextthought.com' % time.time(), 'temp001')
		createdlist = self.ds.createFriendsListWithNameAndFriends(self.CONTAINER, [self.target[0]], credentials=newUser)
		self.ds.waitForEvent()

		targetUserObject = self.ds.getUserObject(credentials=self.target)

		targetNotificationCount = startingCount + 1
		assert_that(targetUserObject, notification_count(greater_than_or_equal_to(targetNotificationCount)))

		startingCount = get_notification_count(targetUserObject)

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdlist, credentials=newUser)

	def test_user_keeps_deleting_note(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0], adapt=True)

		self.ds.deleteObject(createdObj)

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		try:

			# check that the user can now see it
			ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)

		except urllib2.HTTPError: pass

		assert_that(ugd, is_not(contains(sharedObj)))

	def test_bounded_server_stream(self):

		notes_array = []

		FIRST_SHARE = 0

		NUMBER_OF_SHARES = 50

		notes = 0

		while notes < NUMBER_OF_SHARES:

			# create the object to share
			createdObj =  self.ds.createNote('Note number %s' % notes, self.CONTAINER, adapt=True)

			#appends the newly created note to the array
			notes_array.append(createdObj)

			# do the actual sharing
			self.ds.shareObject(createdObj, self.target[0], adapt=True)

			#increments the value of notes
			notes += 1

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		initial_stream = self.ds.getRecursiveStreamData(self.CONTAINER, credentials=self.target)
		initial_sortedchanges = sortchanges(objectsFromContainer(initial_stream))

		# create the object to share
		createdObj =  self.ds.createNote('Note number %s' % notes, self.CONTAINER, adapt=True)

		#appends the newly created note to the array
		notes_array.append(createdObj)

		# do the actual sharing
		self.ds.shareObject(createdObj, self.target[0], adapt=True)

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		final_stream = self.ds.getRecursiveStreamData(self.CONTAINER, credentials=self.target)
		final_sortedchanges = sortchanges(objectsFromContainer(final_stream))

		#cleanup
		while notes >= FIRST_SHARE:

			#deletes the object at the index
			self.ds.deleteObject(notes_array[notes])

			#decrements the value from nates
			notes -= 1

		assert_that(initial_stream, is_(container()))
		assert_that( initial_sortedchanges, has_length( greater_than_or_equal_to( NUMBER_OF_SHARES ) ) )
		assert_that(initial_sortedchanges[NUMBER_OF_SHARES-1], wraps_item(notes_array[0]))
		assert_that(initial_sortedchanges[FIRST_SHARE], wraps_item(notes_array[NUMBER_OF_SHARES - 1]))
		assert_that(final_stream, is_(container()))
		assert_that(final_sortedchanges[NUMBER_OF_SHARES], is_not(wraps_item(notes_array[0])))
		assert_that(final_sortedchanges[NUMBER_OF_SHARES], (wraps_item(notes_array[1])))
		assert_that(final_sortedchanges[FIRST_SHARE+1], wraps_item(notes_array[NUMBER_OF_SHARES]))



if __name__ == '__main__':
	unittest.main()

