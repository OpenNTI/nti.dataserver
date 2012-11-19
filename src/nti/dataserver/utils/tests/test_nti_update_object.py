import os
import json
import unittest

import nti.dataserver
from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.utils import nti_update_object as nuo

from nti.ntiids.ntiids import make_ntiid

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not)

class TestNTIUpdate(ConfiguringTestBase):
	
	set_up_packages = (nti.dataserver,)
	
	@classmethod
	def setUpClass(cls):	
		path = os.path.join(os.path.dirname(__file__), 'update.json')
		with open(path, "r") as f:
			cls.update_json = f.read()
			cls.update_dict = json.loads(cls.update_json)
			
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
		
	def create_note(self, text, user, containerId=None, inReplyTo=None, references=()):
		note = Note()
		note.body = [text]
		note.creator = user
		note.setInReplyTo(inReplyTo)
		for r in references or ():
			note.addReference(r)
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		
		mock_dataserver.current_transaction.add(note)
		note = user.addContainedObject( note ) 	
		return note

	@WithMockDSTrans
	def test_simple_proc_update(self):
		usr = self._create_user()
		note = self.create_note('my note', usr)
		assert_that(note.selectedText, is_(u''))
		assert_that(note.applicableRange, is_(None))
		note = nuo.process_update(note.id, self.update_json)
		assert_that(note.selectedText, is_(u'My selectedText'))
		assert_that(note.applicableRange, is_not(None))

if __name__ == '__main__':
	unittest.main()
	
		
