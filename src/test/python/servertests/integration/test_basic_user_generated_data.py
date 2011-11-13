import time

from servertests import DataServerTestCase

from servertests.integration import contained_in
from servertests.integration import contains
from servertests.integration import objectFromContainer
from servertests.integration import container_of_length

from hamcrest import is_not
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import assert_that

class TestBasicUserGeneratedData(DataServerTestCase):

	USER = ('test.user.1@nextthought.com', 'temp001')

	def setUp(self):
		super(TestBasicUserGeneratedData, self).setUp()
		self.CONTAINER = 'TestBasicUGD-container-%s' % time.time()
		self.ds.setCredentials(self.USER)

		#We clean these up in different places for each test
		self.createdNote = self.ds.createNote("A note to test with", self.CONTAINER)
		self.createdHighlight = self.ds.createHighlight('but', self.CONTAINER,)

	def test_created_objects_show_in_ugd(self):
		ugd = self.ds.getUserGeneratedData(self.CONTAINER)

		assert_that(ugd, is_(container_of_length(2)))
		assert_that(ugd, contains(self.createdNote))
		assert_that(ugd, contains(self.createdHighlight))

		# cleanup
		self.ds.deleteObject(self.createdNote)
		self.ds.deleteObject(self.createdHighlight)


	def test_delete_removes_from_ugd(self):
		ugd = self.ds.getUserGeneratedData(self.CONTAINER)

		assert_that(ugd, is_(container_of_length(2)))
		assert_that(ugd, contains(self.createdNote))
		assert_that(ugd, contains(self.createdHighlight))

		# cleanup
		self.ds.deleteObject(self.createdNote)
		self.ds.deleteObject(self.createdHighlight)

		ugd = self.ds.getUserGeneratedData(self.CONTAINER)
		assert_that(ugd, is_(container_of_length(0)))
		assert_that(self.createdNote, is_not(contained_in(ugd)))
		assert_that(self.createdHighlight, is_not(contained_in(ugd)))

	def test_update_reflects_in_ugd(self):
		ugd = self.ds.getUserGeneratedData(self.CONTAINER)

		assert_that(ugd, is_(container_of_length(2)))
		assert_that(ugd, contains(self.createdNote))
		assert_that(ugd, contains(self.createdHighlight))

		self.createdHighlight['startHighlightedText'] = 'new'
		updatedHighlight = self.ds.updateObject(self.createdHighlight)

		ugd = self.ds.getUserGeneratedData(self.CONTAINER)

		assert_that(ugd, is_(container_of_length(2)))
		assert_that(ugd, contains(self.createdNote))
		assert_that(ugd, contains(self.createdHighlight))

		ugdHighlight = objectFromContainer(ugd, updatedHighlight)
		assert_that(ugdHighlight, has_entry('startHighlightedText', 'new'))

		# cleanup
		self.ds.deleteObject(self.createdNote)
		self.ds.deleteObject(self.createdHighlight)

if __name__ == '__main__':
	import unittest
	unittest.main()
