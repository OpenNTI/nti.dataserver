import unittest

from hamcrest import equal_to
from hamcrest import assert_that

from nti.dataserver.activitystream_change import Change
from nti.contentsearch._indexagent import _process_event

from nti.contentsearch.tests import ConfiguringTestBase

test_user = 'test.user@nextthought.com'

note_add =  {'body': [u'Kenpachi Zaraki'], 'ContainerId': 'tag:nextthought.com,2011-07-14:AOPS-HTML-prealgebra-0', \
			'Creator': test_user, 'Last Modified': 1321473657.231101, 'text': u'Kenpachi Zaraki',\
			'OID': '0x39:5573657273', 'ID': '3', 'CreatedTime': 1321473657.230834, 'Class': 'Note'}


note_mod = {'body': [u'Kenpachi Zaraki and&nbsp;Yachiru Kusajishi for the 11th Division'], \
		 	'ContainerId': 'tag:nextthought.com,2011-07-14:AOPS-HTML-prealgebra-0', 'Creator': test_user, \
		 	'Last Modified': 1321473759.952458, 'text': u'Kenpachi Zaraki and&nbsp;Yachiru Kusajishi for the 11th Division',
		 	'OID': '0x39:5573657273', 'ID': '3', 'CreatedTime': 1321473657.230834, 'Class': 'Note'}

def decorator(f):
	def execute(self, *args, **kwargs):
		self.exception = None
		try:
			f(self, *args, **kwargs)
		except Exception as e:
			self.exception = e
	execute.__name__ = f.__name__
	return execute

class MockIndexManager(object):

	def __init__(self):
		self.exception = None

	@decorator
	def index_user_content(self, username, type_name=None, data=None, *args, **kwargs):
		assert_that('Note', equal_to(type_name))
		assert_that(username, equal_to(test_user))
		assert_that(note_add, equal_to(data))

	@decorator
	def update_user_content(self, username, type_name=None, data=None, *args, **kwargs):
		assert_that('Note', equal_to(type_name))
		assert_that(username, equal_to(test_user))
		assert_that(note_mod, equal_to(data))

	@decorator
	def delete_user_content(self, username, type_name=None, data=None, *args, **kwargs):
		self.update_user_content(username, type_name, data)

class TestIndexAgent(ConfiguringTestBase):

	indexmanager = None

	def setUp(self):
		super(TestIndexAgent, self).setUp()
		self.indexmanager = MockIndexManager()

	def test_create(self):
		_process_event(self.indexmanager, test_user, Change.CREATED, 'Note', note_add)
		if self.indexmanager.exception:
			self.fail(str(self.indexmanager.exception))

	def test_update(self):
		_process_event(self.indexmanager, test_user, Change.MODIFIED, 'Note', note_mod)
		if self.indexmanager.exception:
			self.fail(str(self.indexmanager.exception))

	def test_delete(self):
		_process_event(self.indexmanager, test_user, Change.DELETED, 'Note', note_mod)
		if self.indexmanager.exception:
			self.fail(str(self.indexmanager.exception))

if __name__ == '__main__':
	unittest.main()
