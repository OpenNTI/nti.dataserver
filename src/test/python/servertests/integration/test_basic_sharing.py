import time
import urllib2

from servertests import DataServerTestCase
from servertests.integration import contained_in
from servertests.integration import shared_with
from servertests.integration import has_same_oid_as
from servertests.integration import contains

from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import is_

class TestBasicSharing(DataServerTestCase):

	owner = ('test.user.1@nextthought.com', 'temp001')
	target = ('test.user.2@nextthought.com', 'temp001')
	unauthorized_target = ('test.user.3@nextthought.com', 'incorrect')
	noteToCreateAndShare = {'text': 'A note to share'}

	def setUp(self):
		super(TestBasicSharing, self).setUp()

		#Changes can't go to users that dont exist so we make sure to autocreate them
		self.ds.getRecursiveStreamData('dontcare', credentials=self.owner)
		self.ds.getRecursiveStreamData('dontcare', credentials=self.target)

		self.CONTAINER = 'TestBasicStream-container-%s' % time.time()
		self.ds.setCredentials(self.owner)

	def test_basic_sharing(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0], adapt=True)
		assert_that(sharedObj, has_same_oid_as(createdObj))
		assert_that(sharedObj, shared_with(self.target[0]))

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		
		assert_that(ugd, contains(sharedObj))

		# cleanup
		self.ds.deleteObject(createdObj)
		
	def test_basic_sharing_incorrect_data(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		otherObj =  self.ds.createNote('A note not to share', self.CONTAINER, adapt=True)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0], adapt=True)
		assert_that(sharedObj, has_same_oid_as(createdObj))
		assert_that(sharedObj, shared_with(self.target[0]))

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)

		assert_that(ugd, is_not(contains(otherObj)))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(otherObj)

	def test_sharing_multiple_data(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		otherObj =  self.ds.createNote('A note not to share', self.CONTAINER, adapt=True)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0], adapt=True)
		assert_that(sharedObj, has_same_oid_as(createdObj))
		assert_that(sharedObj, shared_with(self.target[0]))
		
		sharedObj = self.ds.shareObject(otherObj, self.target[0], adapt=True)
		assert_that(sharedObj, has_same_oid_as(otherObj))
		assert_that(sharedObj, shared_with(self.target[0]))

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)

		assert_that(ugd, contains(otherObj))
		assert_that(ugd, contains(createdObj))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(otherObj)


	def test_revoke_sharing(self):
		# create the object to share
		createdObj = self.ds.createNote('A note to share', self.CONTAINER)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0])
		assert_that(sharedObj, has_same_oid_as(createdObj))
		assert_that(sharedObj, shared_with(self.target[0]))

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target)
		assert_that(ugd, contains(sharedObj))

		# unshare it
		unSharedObj = self.ds.unshareObject(sharedObj, self.target[0])
		assert_that(unSharedObj, has_same_oid_as(createdObj))
		assert_that(unSharedObj, is_not(shared_with(self.target[0])))

		# make sure target can't see it
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that the user can now see it
		container = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target)
		assert_that(createdObj, is_not(contained_in(container)))

		# cleanup
		self.ds.deleteObject(createdObj)
		
	def test_revoke_selected_share(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		otherObj =  self.ds.createNote('A note not to share', self.CONTAINER, adapt=True)

		# do the actual sharing
		sharedObj1 = self.ds.shareObject(createdObj, self.target[0], adapt=True)
		assert_that(sharedObj1, has_same_oid_as(createdObj))
		assert_that(sharedObj1, shared_with(self.target[0]))
		
		sharedObj2 = self.ds.shareObject(otherObj, self.target[0], adapt=True)
		assert_that(sharedObj2, has_same_oid_as(otherObj))
		assert_that(sharedObj2, shared_with(self.target[0]))
		
		unSharedObj = self.ds.unshareObject(sharedObj1, self.target[0])
		assert_that(unSharedObj, has_same_oid_as(createdObj))
		assert_that(unSharedObj, is_not(shared_with(self.target[0])))

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)

		assert_that(ugd, contains(otherObj))
		assert_that(ugd, is_not(contains(createdObj)))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(otherObj)
		
	def test_share_not_found(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		#delete note
		self.ds.deleteObject(createdObj)
		sharedObj1 = None

		# do the actual sharing
		try:
			sharedObj1 = self.ds.shareObject(createdObj, self.target[0], adapt=True)
			# we aren't instant	Wait some arbitrary time.
			self.ds.waitForEvent()
		except urllib2.HTTPError: pass
		
		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		
		assert_that(sharedObj1, is_(None))
		assert_that(ugd, is_not(contains(createdObj)))
		
	def test_unauthorized_sharing(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)

		sharedObj = None

		# do the actual sharing
		try:
			sharedObj = self.ds.shareObject(createdObj, self.unauthorized_target, adapt=True)
		
		except urllib2.HTTPError, code: pass

		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		
		assert_that(sharedObj, is_(None))
		assert_that(ugd, is_not(contains(createdObj)))
		assert_that(code, 401)

		# cleanup
		self.ds.deleteObject(createdObj)
		
	def test_user_keeps_deleting_note(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)

		# do the actual sharing
		sharedObj = self.ds.shareObject(createdObj, self.target[0], adapt=True)

		#removes the object after sharing
		self.ds.deleteObject(createdObj)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		#creates the variable ugd
		ugd = None

		# attempt to find the note that was shared by the first user
		try:
			ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
			
		# catches an exception if the note is not found
		except urllib2.HTTPError: pass
		
		#asserts that the shared object contains none.
		assert_that(ugd, is_not(contains(sharedObj)))
		
	def test_create_and_share_note(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, sharedWith=[self.owner[0], self.target[0]], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()

		assert_that(createdObj['body'][0], is_('A note to share'))
		assert_that(createdObj['sharedWith'], is_([self.target[0]]))

		# cleanup
		self.ds.deleteObject(createdObj)
		
	def test_share_note_through_dict(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, sharedWith=[self.owner[0], self.target[0]], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		sharedObj = self.ds.sharedObjWithID(createdObj['id'], [self.owner[0], self.target[0]])
		
		assert_that(sharedObj['sharedWith'], is_(['test.user.2@nextthought.com']))
		
if __name__ == '__main__':
	import unittest
	unittest.main()

