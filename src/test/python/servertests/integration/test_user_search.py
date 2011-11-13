import uuid

from servertests import DataServerTestCase
from servertests.integration import container
from servertests.integration import container_of_length

from hamcrest import assert_that

class TestUserSearch(DataServerTestCase):

	def setUp(self):
		super(TestUserSearch, self).setUp()
		self.PREFIX = 'test.user'
		self.CONTAINER = 'container-%s' % uuid.uuid1()
		self.USERS = [('%s.%s@nextthought.com' % (self.PREFIX, r), 'temp001') for r in xrange(15,19)]

	def _create_note_object(self, client, note, container):
		return client.createObject(note, objType='Note', container=container)

	def _create_users_notes(self, container):
		objects =[]
		for f in self.USERS:
			username = f[0]
			note = {'text': 'Fake note owned by %s' % username}
			self.ds.clearCredentials()
			self.ds.setCredentials(f)
			objects.append(self._create_note_object(self.ds, note, container))
		return objects

	def _delete_user_notes(self, objects):
		it = iter(objects)
		for f in self.USERS:
			self.ds.clearCredentials()
			self.ds.setCredentials(f)
			self.ds.deleteObject(it.next())

	def test_search_users(self):

		objects = self._create_users_notes(self.CONTAINER)
		self.ds.setCredentials(self.USERS[0])

		result = self.ds.executeUserSearch(self.PREFIX)
		assert_that(result, container())
		self.assertGreaterEqual(len(result['Items']), 4)

		result = self.ds.executeUserSearch("%s.15" % self.PREFIX)
		assert_that(result, container_of_length(1))

		# not a reg exp
		result = self.ds.executeUserSearch("%s.2*" % self.PREFIX)
		assert_that(result, container_of_length(0))

		result = self.ds.executeUserSearch("%s.35" % self.PREFIX)
		assert_that(result, container_of_length(0))

		self._delete_user_notes(objects)

if __name__ == '__main__':
	import unittest
	unittest.main()
