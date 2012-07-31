import os
import json
import unittest

from nti.externalization.externalization import toExternalObject

from nti.contentsearch.common import get_type_name
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch._search_external import _NoteSearchHit
from nti.contentsearch._search_external import _HighlightSearchHit
from nti.contentsearch._search_external import _RedactionSearchHit
from nti.contentsearch._search_external import _MessageInfoSearchHit
from nti.contentsearch._search_external import _provide_highlight_snippet

from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.common import (NTIID, CREATOR, CONTAINER_ID, CLASS, HIT, SNIPPET, TARGET_OID)

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
			
		path = os.path.join(os.path.dirname(__file__), 'note2.json')
		with open(path, "r") as f:
			cls.note2 = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'redaction.json')
		with open(path, "r") as f:
			cls.redaction = json.load(f)
			
	def _externalize(self, clazz, data, query):
		d = _provide_highlight_snippet(clazz(data), query)
		return toExternalObject(d)
		
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
			has_entry(SNIPPET, u'You know how to add subtract multiply and DIVIDE In fact you may already know how to solve many of the problems'))
		
	def test_searh_hit_redaction_dict(self):
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
		assert_that(d, has_entry(SNIPPET, u'All WAVES Rise now and Become my Shield Lightning Strike now and'))
		
	def test_search_hit_messgeinfo_dict(self):
		d = self._externalize(_MessageInfoSearchHit, self.messageinfo, '')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x82:53657373696f6e73'))
		assert_that(d, has_entry(CREATOR, u'troy.daley@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73'))
		assert_that(d, has_entry(TARGET_OID, u'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73'))
		assert_that(d, has_entry(SNIPPET, u'Zanpakuto and Zangetsu'))
		
	def test_get_type_name(self):
		assert_that(get_type_name(self.note), is_('note'))
		assert_that(get_type_name(self.hightlight), is_('highlight'))
		assert_that(get_type_name(self.messageinfo), is_('messageinfo'))

if __name__ == '__main__':
	unittest.main()
