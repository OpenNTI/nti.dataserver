'''
Created on Nov 2, 2011

@author: ltesti
'''

import time
import urllib2

from servertests import DataServerTestCase
from servertests.integration import contains

from hamcrest import assert_that
from hamcrest import is_not
from hamcrest import is_

class TestBasicReplying(DataServerTestCase):
	owner = ('test.user.1@nextthought.com', 'temp001')
	target = ('test.user.2@nextthought.com', 'temp001')

	def setUp(self):
		super(TestBasicReplying, self).setUp()

		# FIXME:  This is duplicated in alot of places.
		self.ds.getRecursiveStreamData('autocreate', credentials=self.owner)
		self.ds.getRecursiveStreamData('autocreate', credentials=self.target)

		self.CONTAINER = 'test.user.container.%s' % time.time()
		self.ds.setCredentials(self.owner)

	def test_create_basic_reply(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		# creates a reply to the note
		createdReply = self.ds.createNote("A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		assert_that(createdReply['body'][0]), is_("A reply to note")
		assert_that(createdReply['inReplyTo'], is_(createdObj['id']))
		assert_that(createdReply['references'], is_(None))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdReply)
		
	def test_share_basic_reply(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		# do the actual sharing
		self.ds.shareObject(createdObj, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# creates a reply to the note
		createdReply = self.ds.createNote("A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdReply, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.owner, adapt=True)
		assert_that(ugd, contains(createdReply))
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		assert_that(ugd, contains(createdReply))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdReply)
		
	def test_revoke_basic_reply(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		# do the actual sharing
		self.ds.shareObject(createdObj, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# creates a reply to the note
		createdReply = self.ds.createNote("A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdReply, self.target[0], adapt=True)
		
		self.ds.unshareObject(createdReply, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.owner, adapt=True)
		assert_that(ugd, contains(createdReply))
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		assert_that(createdReply['sharedWith'], is_not(self.target[0]))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdReply)
		
	def test_revoke_note_with_reply(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		# do the actual sharing
		self.ds.shareObject(createdObj, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# creates a reply to the note
		createdReply = self.ds.createNote("A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdReply, self.target[0], adapt=True)
		
		self.ds.unshareObject(createdObj, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.owner, adapt=True)
		assert_that(ugd, contains(createdReply))
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		assert_that(createdReply['sharedWith'], is_not(self.target[0]))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdReply)
		
	def test_delete_shared_reply(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		# do the actual sharing
		self.ds.shareObject(createdObj, self.target[0], adapt=True)
		
		# creates a reply to the note
		createdReply = self.ds.createNote("A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdReply, self.target[0], adapt=True)

		# delete the test
		self.ds.deleteObject(createdReply)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.owner, adapt=True)
		assert_that(ugd, is_not(contains(createdReply)))
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		assert_that(ugd, contains(createdReply))
		
		# cleanup
		self.ds.deleteObject(createdObj)
		
	def test_replying_to_own_reply(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		# do the actual sharing
		self.ds.shareObject(createdObj, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# creates a reply to the note
		createdReply = self.ds.createNote("A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdReply, self.target[0], adapt=True)
		
		createdPSReply = self.ds.createNote("PS. A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdPSReply, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.owner, adapt=True)
		assert_that(ugd, contains(createdPSReply))
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		assert_that(ugd, contains(createdPSReply))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdReply)
		self.ds.deleteObject(createdPSReply)
		
	def test_replying_to_other_reply(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		# do the actual sharing
		self.ds.shareObject(createdObj, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# creates a reply to the note
		createdReply = self.ds.createNote("A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdReply, self.target[0], adapt=True)
		
		createdResponseReply = self.ds.createNote("A reply to a reply", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdResponseReply, self.owner[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.owner, adapt=True)
		assert_that(ugd, contains(createdResponseReply))
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		assert_that(ugd, contains(createdResponseReply))

		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdReply)
		self.ds.deleteObject(createdResponseReply)
		
	def test_delete_basic_reply_by_other_user(self):
		# create the object to share
		createdObj =  self.ds.createNote('A note to share', self.CONTAINER, adapt=True)
		
		# do the actual sharing
		self.ds.shareObject(createdObj, self.target[0], adapt=True)
		
		# we aren't instant	Wait some arbitrary time.
		self.ds.waitForEvent()
		
		# creates a reply to the note
		createdReply = self.ds.createNote("A reply to note", self.CONTAINER, inReplyTo=createdObj['id'], adapt=True)
		
		self.ds.shareObject(createdReply, self.target[0], adapt=True)

		try:
			# delete the test
			self.ds.deleteObject(createdReply, credentials=self.target)
			
		except urllib2.HTTPError, response: pass
		
		# check that the user can now see it
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.owner, adapt=True)
		assert_that(ugd, contains(createdReply))
		ugd = self.ds.getUserGeneratedData(self.CONTAINER, credentials=self.target, adapt=True)
		assert_that(ugd, contains(createdReply))
		assert_that(response.code, is_(403))
		
		# cleanup
		self.ds.deleteObject(createdObj)
		self.ds.deleteObject(createdReply)
		
if __name__ == '__main__':
	import unittest
	unittest.main()