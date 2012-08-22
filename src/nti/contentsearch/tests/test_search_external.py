import os
import json
import time
import unittest
from datetime import datetime

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Highlight
from nti.dataserver.contenttypes import Redaction

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import toExternalObject

from nti.contentsearch.common import get_type_name
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch._search_external import _NoteSearchHit
from nti.contentsearch._search_external import _HighlightSearchHit
from nti.contentsearch._search_external import _RedactionSearchHit
from nti.contentsearch._search_external import _WhooshBookSearchHit
from nti.contentsearch._search_external import _MessageInfoSearchHit
from nti.contentsearch._search_external import _provide_highlight_snippet

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.common import (NTIID, CREATOR, CONTAINER_ID, CLASS, TYPE, HIT, SNIPPET, TARGET_OID)
from nti.contentsearch.common import (ntiid_, content_, title_, last_modified_)
									
from hamcrest import (assert_that, is_, is_not, has_entry)

class TestRepozeIndex(ConfiguringTestBase):
		
	@classmethod
	def setUpClass(cls):		
		path = os.path.join(os.path.dirname(__file__), 'highlight.json')
		with open(path, "r") as f:
			cls.hightlight = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'note.json')
		with open(path, "r") as f:
			cls.note = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'redaction.json')
		with open(path, "r") as f:
			cls.redaction = json.load(f)
			
	def _create_user(self, ds=None, username='nt@nti.com', password='temp001'):
		ds = ds or mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
	def _externalize(self, clazz, data, query):
		d = _provide_highlight_snippet(clazz(data), query)
		return toExternalObject(d)
			
	def test_get_type_name(self):
		assert_that(get_type_name(self.note), is_('note'))
		assert_that(get_type_name(self.hightlight), is_('highlight'))
		assert_that(get_type_name(self.messageinfo), is_('messageinfo'))
		
	def test_get_search_hit(self):
		hit = get_search_hit({})
		assert_that(hit, is_not(None))
			
	def test_search_hit_hightlight_dict(self):
		d = self._externalize(_HighlightSearchHit, self.hightlight, 'divide')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(d, has_entry(CREATOR, u'carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'))
		assert_that(d, has_entry(TARGET_OID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'))
		assert_that(d,
			has_entry(SNIPPET, u'you know how to add subtract multiply and DIVIDE in fact you may already know how to solve many of the problems'))
		
	def test_seach_hit_redaction_dict(self):
		d = self._externalize(_RedactionSearchHit, self.redaction, '')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:AOPS-HTML-Howes_converted.0'))
		assert_that(d, has_entry(CREATOR, u'carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x1876:5573657273'))
		assert_that(d, has_entry(TARGET_OID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x1876:5573657273'))
		assert_that(d, has_entry(SNIPPET, u'redaction serving a sentence in a Michigan jail'))
		
	def test_search_hit_note_dict(self):
		d = self._externalize(_NoteSearchHit, self.note, 'waves')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(d, has_entry(CREATOR, u'carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0860:5573657273'))
		assert_that(d, has_entry(TARGET_OID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0860:5573657273'))
		assert_that(d, has_entry(SNIPPET, u'all WAVES rise now and become my shield lightning strike now and'))
		
	def test_search_hit_messgeinfo_dict(self):
		d = self._externalize(_MessageInfoSearchHit, self.messageinfo, '')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x82:53657373696f6e73'))
		assert_that(d, has_entry(CREATOR, u'troy.daley@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73'))
		assert_that(d, has_entry(TARGET_OID, u'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73'))
		assert_that(d, has_entry(SNIPPET, u'Zanpakuto and Zangetsu'))
		
	@WithMockDSTrans
	def test_search_hit_note_ds(self):
		usr = self._create_user()
		note = Note()
		note.body = [u'It is not enough to mean well, we actually have to do well']
		note.creator =  usr.username
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		mock_dataserver.current_transaction.add(note)
		note = usr.addContainedObject( note ) 
		oidstr = to_external_ntiid_oid(note)
		d = self._externalize(_NoteSearchHit, note, 'well')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(TYPE, 'Note'))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(d, has_entry(CREATOR, u'nt@nti.com'))
		assert_that(d, has_entry(NTIID, oidstr))
		assert_that(d, has_entry(TARGET_OID, oidstr))
		assert_that(d, has_entry(SNIPPET, u'it is not enough to mean WELL we actually have to do WELL'))
		
	@WithMockDSTrans
	def test_search_hit_hightlight_ds(self):
		usr = self._create_user()
		highlight = Highlight()
		highlight.selectedText = u'Kon saw it! The Secret of a Beautiful Office Lady'
		highlight.creator = usr.username
		highlight.containerId =  make_ntiid(nttype='bleach', specific='manga')
		highlight = usr.addContainedObject( highlight )
		oidstr = to_external_ntiid_oid(highlight)
		d = self._externalize(_HighlightSearchHit, highlight, 'secret')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(TYPE, 'Highlight'))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(d, has_entry(CREATOR, u'nt@nti.com'))
		assert_that(d, has_entry(NTIID, oidstr))
		assert_that(d, has_entry(TARGET_OID, oidstr))
		assert_that(d, has_entry(SNIPPET, u'kon saw it the SECRET of a beautiful office lady'))
		
	@WithMockDSTrans
	def test_search_hit_redaction_ds(self):
		usr = self._create_user()
		redaction = Redaction()
		redaction.selectedText = u'Fear'
		redaction.replacementContent = 'redaction'
		redaction.redactionExplanation = 'Have overcome it everytime I have been on the verge of death'
		redaction.creator = usr.username
		redaction.containerId =  make_ntiid(nttype='bleach', specific='manga')
		redaction = usr.addContainedObject( redaction )
		oidstr = to_external_ntiid_oid(redaction)
		d = self._externalize(_RedactionSearchHit, redaction, 'death')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(TYPE, 'Redaction'))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(d, has_entry(CREATOR, u'nt@nti.com'))
		assert_that(d, has_entry(NTIID, oidstr))
		assert_that(d, has_entry(TARGET_OID, oidstr))
		assert_that(d, has_entry(SNIPPET, u'overcome it everytime i have been on the verge of DEATH fear'))

	def test_search_hit_book(self):
		containerId = make_ntiid(nttype='bleach', specific='manga')	
		hit = {}
		hit[title_] = 'Bleach'
		hit[ntiid_] = containerId
		hit[last_modified_] = datetime.fromtimestamp(time.time())
		hit[content_] = u'All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'
		d = self._externalize(_WhooshBookSearchHit, hit, 'shield')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(TYPE, 'Content'))
		assert_that(d, has_entry(CONTAINER_ID, containerId))
		assert_that(d, has_entry(NTIID, containerId))
		assert_that(d, has_entry(SNIPPET, u'all waves, rise now and become my SHIELD, lightning, strike now and become my blade'))
		
if __name__ == '__main__':
	unittest.main()
