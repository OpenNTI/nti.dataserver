import time

from servertests import DataServerTestCase

from servertests.integration import notification_count
from servertests.integration import get_notification_count

from hamcrest import assert_that
from hamcrest import equal_to 

class TestUserObject(DataServerTestCase):
	user_one = ('test.user.6@nextthought.com', 'temp001')
	user_two = ('test.user.7@nextthought.com', 'temp001')

	def setUp(self):
		super(TestUserObject, self).setUp()

		# FIXME:  This is duplicated in alot of places.
		self.ds.getRecursiveStreamData('autocreate', credentials=self.user_one)
		self.ds.getRecursiveStreamData('autocreate', credentials=self.user_two)

		self.CONTAINER = 'test.user.container.%s' % time.time()
		self.ds.setCredentials(self.user_one)

	def test_notification_count_can_reset(self):
		user1Object = self.ds.getUserObject()

		createdObjects = []
		if get_notification_count(user1Object) < 2:
			for _ in xrange(3):
				createdObj = self.ds.createNote('A note to share', self.CONTAINER, credentials=self.user_two)
				self.ds.shareObject(createdObj, self.user_one[0], credentials=self.user_two)
				createdObjects.append(createdObj)

		updateLastLogin = {'lastLoginTime': time.time()}
		user1Object = self.ds.updateObject(updateLastLogin, oid=user1Object['OID'])

		assert_that(user1Object, notification_count(equal_to(0)))

		for createdObject in createdObjects:
			self.ds.deleteObject(createdObject, credentials=self.user_two)

if __name__ == '__main__':
	import unittest
	unittest.main()

