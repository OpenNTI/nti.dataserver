import unittest

import nti.dataserver
from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.utils import nti_delete_user_objects as nti_delete

from nti.ntiids.ntiids import make_ntiid

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.ntiids import ntiids

import nti.contentsearch

from nti.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_entry)

class TestNTIDeleteUserObjects(ConfiguringTestBase):
	
	set_up_packages = (nti.dataserver,nti.contentsearch)
			
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
	def test_simple_delete(self):
		usr = self._create_user()
		note = self.create_note('my note', usr)
		oid = note.id
		cmap, _ = nti_delete.delete_entity_objects(usr)
		assert_that(cmap, has_entry('note', is_(1)))
		note = ntiids.find_object_with_ntiid(oid)
		assert_that(note, is_(None))
		
if __name__ == '__main__':
	unittest.main()
	
		
