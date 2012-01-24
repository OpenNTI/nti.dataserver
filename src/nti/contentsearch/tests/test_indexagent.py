import unittest

from hamcrest import equal_to
from hamcrest import assert_that

from nti.dataserver.users import Change
from nti.contentsearch._indexagent import IndexAgent

##########################

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
		except Exception, e:
			self.exception = e
			
	return execute
			
class MockIndexManager():
	
	def __init__(self):
		self.exception = None
		
	@decorator
	def index_user_content(self, externalValue, username, typeName):
		assert_that('Note', equal_to(typeName))
		assert_that(username, equal_to(test_user))
		assert_that(note_add, equal_to(externalValue))

	@decorator
	def update_user_content(self, externalValue, username, typeName):
		assert_that('Note', equal_to(typeName))
		assert_that(username, equal_to(test_user))
		assert_that(note_mod, equal_to(externalValue))

	@decorator
	def delete_user_content(self, externalValue, username, typeName):
		self.update_user_content(externalValue, username, typeName)
		
##########################
	
class TestIndexAgent(unittest.TestCase):
	
	indexagent = None
	indexmanager = None
		
	@classmethod
	def setUpClass(cls):
		cls.indexmanager = MockIndexManager()
		cls.indexagent = IndexAgent(cls.indexmanager)
		
	def test_create(self):
		event = self.indexagent._create_event(test_user, Change.CREATED, 'Note', note_add)
		self.indexagent._handle_event(event).run()
		if self.indexmanager.exception:
			self.fail(str(self.indexmanager.exception))
					
	def test_update(self):
		event = self.indexagent._create_event(test_user, Change.MODIFIED, 'Note', note_mod)
		self.indexagent._handle_event(event).run()
		if self.indexmanager.exception:
			self.fail(str(self.indexmanager.exception))
		
	def test_delete(self):
		event = self.indexagent._create_event(test_user, Change.DELETED, 'Note', note_mod)
		self.indexagent._handle_event(event).run()
		if self.indexmanager.exception:
			self.fail(str(self.indexmanager.exception))
		
	@classmethod
	def tearDownClass(cls):
		cls.indexagent.close()

if __name__ == '__main__':
	unittest.main()
	
