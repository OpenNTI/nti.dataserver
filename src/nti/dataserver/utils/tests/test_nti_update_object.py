import os
import json
import unittest

import nti.dataserver
from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Redaction
from nti.dataserver.utils import nti_update_object as nti_update

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
		note = nti_update.process_update(note.id, self.update_json)
		assert_that(note.selectedText, is_(u'My selectedText'))
		assert_that(note.applicableRange, is_not(None))
		
	@WithMockDSTrans
	def test_simple_cascade(self):
		aizen = self._create_user('aizen@nt.com')
		note_a = self.create_note('Leader of the Arrancar Army', aizen)
		grimmjow = self._create_user('grimmjow@nt.com')
		note_g = self.create_note("6th Espada in Aizen's Army", grimmjow,
								  note_a.containerId, inReplyTo=note_a, references=(note_a,))
		assert_that(note_g.selectedText, is_(u''))
		assert_that(note_g.applicableRange, is_(None))
		assert_that(note_g.inReplyTo, is_(note_a))
		assert_that(note_g.references, is_([note_a]))
		
		# update
		nti_update.process_update(note_a.id, self.update_json, cascade=True)
		
		# check master note
		note_a = nti_update.find_object(note_a.id)
		assert_that(note_a.selectedText, is_(u'My selectedText'))
		assert_that(note_a.applicableRange, is_not(None))
		
		# check slave_note
		note_g = nti_update.find_object(note_g.id)
		assert_that(note_g.selectedText, is_(u''))
		assert_that(note_g.applicableRange, is_not(None))
		assert_that(note_g.inReplyTo, is_(note_a))
		assert_that(note_g.references, is_([note_a]))

	@WithMockDSTrans
	def test_with_redaction_no_cascade(self):
		user = self._create_user('tolkien@nt.com')
		redaction = Redaction()
		redaction.selectedText = u'Iluvatar'
		redaction.replacementContent = u'Eru'
		redaction.redactionExplanation = u'Supreme god of Arda and Middle-earth.'
		redaction.creator = user
		redaction.containerId = make_ntiid(nttype='book', specific='silmarillion')
		mock_dataserver.current_transaction.add(redaction)
		redaction = user.addContainedObject( redaction )
		
		note = self.create_note("Father of All", user,
								 redaction.containerId, inReplyTo=redaction, references=(redaction,))
		
		assert_that(note.inReplyTo, is_(redaction))
		assert_that(note.references, is_([redaction]))
		assert_that(note.applicableRange, is_(None))
		
		# update
		redaction = nti_update.process_update(redaction.id, self.update_json, cascade=True)
		assert_that(redaction.selectedText, is_(u'My selectedText'))
		assert_that(redaction.applicableRange, is_not(None))
		
		note = nti_update.find_object(note.id)
		assert_that(note.inReplyTo, is_(redaction))
		assert_that(note.references, is_([redaction]))
		assert_that(note.selectedText, is_(u''))
		assert_that(note.applicableRange, is_(None)) # None b/c redacions are not thredable
		
	@WithMockDSTrans
	def test_invalid_params(self):
		usr = self._create_user()
		note = self.create_note('my note', usr)
		try:
			nti_update.process_update(note.id, fields=('body="123"',))
			self.fail("should not accepted body field")
		except:
			pass
		
		try:
			nti_update.process_update(note.id, fields=('sharedWith=123',))
			self.fail("should not accepted sharedWith field")
		except:
			pass
		
		try:
			nti_update.process_update(note.id, fields=('selectedText="here"', 'id=123',))
			self.fail("should not accepted id field")
		except:
			pass
		
if __name__ == '__main__':
	unittest.main()
	
		
