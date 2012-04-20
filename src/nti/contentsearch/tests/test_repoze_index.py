import os
import json
import unittest

from nti.externalization.externalization import toExternalObject

from nti.contentsearch.common import get_type_name
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch._search_external import _NoteSearchHit
from nti.contentsearch._search_external import _HighlightSearchHit
from nti.contentsearch._search_external import _MessageInfoSearchHit
from nti.contentsearch._search_external import _provide_highlight_snippet

from nti.contentsearch._repoze_index import get_id
from nti.contentsearch._repoze_index import get_oid
from nti.contentsearch._repoze_index import get_ntiid
from nti.contentsearch._repoze_index import get_creator
from nti.contentsearch._repoze_index import get_channel
from nti.contentsearch._repoze_index import get_keywords
from nti.contentsearch._repoze_index import get_sharedWith
from nti.contentsearch._repoze_index import get_note_ngrams
from nti.contentsearch._repoze_index import get_containerId
from nti.contentsearch._repoze_index import get_note_content
from nti.contentsearch._repoze_index import get_last_modified
from nti.contentsearch._repoze_index import get_highlight_ngrams
from nti.contentsearch._repoze_index import get_highlight_content
from nti.contentsearch._repoze_index import create_notes_catalog
from nti.contentsearch._repoze_index import get_messageinfo_ngrams
from nti.contentsearch._repoze_index import get_messageinfo_content
from nti.contentsearch._repoze_index import create_highlight_catalog
from nti.contentsearch._repoze_index import create_messageinfo_catalog

from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import assert_that
from hamcrest import close_to
from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import greater_than_or_equal_to

from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID,
										COLLECTION_ID, ID, CLASS, HIT, SNIPPET, TARGET_OID)

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_,
										recipients_, sharedWith_)

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
			
	def _test_common_catalog(self, catalog):
		assert_that(catalog, has_key(OID))
		assert_that(catalog, has_key(NTIID))
		assert_that(catalog, has_key(CREATOR))
		assert_that(catalog, has_key(keywords_))
		assert_that(catalog, has_key(sharedWith_))
		assert_that(catalog, has_key(CONTAINER_ID))
		assert_that(catalog, has_key(COLLECTION_ID))
		assert_that(catalog, has_key(LAST_MODIFIED))
		
	def test_get_search_hit(self):
		hit = get_search_hit({})
		assert_that(hit, is_not(None))
		
	def test_notes_catalog(self):
		catalog = create_notes_catalog()
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(references_))
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))
		
	def test_highlight_catalog(self):
		catalog = create_highlight_catalog()
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))
	
	def test_messageinf_catalog(self):
		catalog = create_messageinfo_catalog()
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(ID))
		assert_that(catalog, has_key(channel_))
		assert_that(catalog, has_key(recipients_))
		assert_that(catalog, has_key(references_))
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))
		
	# -------------

	def test_highlight(self):
		obj = self.hightlight
		id_str = 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'
		assert_that(get_id(obj), is_(id_str))
		assert_that(get_oid(obj), is_(id_str))
		assert_that(get_ntiid(obj), is_(id_str))
		assert_that(get_creator(obj), is_('carlos.sanchez@nextthought.com'))
		assert_that(get_keywords(obj), is_({u'operations', u'divide'}))
		assert_that(get_sharedWith(obj), is_([]))
		assert_that(get_containerId(obj), is_('tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		# assert_that(get_collectionId(obj), is_('prealgebra'))
		assert_that(get_last_modified(obj), is_(close_to(1331922120.97, 0.05)))
		assert_that(get_highlight_content(obj), has_length(greater_than_or_equal_to(190)))
		assert_that(get_highlight_ngrams(obj).split(), has_length(69))
		
	def test_note(self):
		obj = self.note
		id_str = 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0860:5573657273'
		assert_that(get_id(obj), is_(id_str))
		assert_that(get_oid(obj), is_(id_str))
		assert_that(get_ntiid(obj), is_(id_str))
		assert_that(get_creator(obj), is_('carlos.sanchez@nextthought.com'))
		assert_that(get_keywords(obj), is_([]))
		assert_that(get_sharedWith(obj), is_([]))
		assert_that(get_containerId(obj), is_('tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		# assert_that(get_collectionId(obj), is_('prealgebra'))
		assert_that(get_last_modified(obj), is_(close_to(1331922201.92, 0.05)))
		assert_that(get_note_content(obj), is_('all waves rise now and become my shield lightning strike now and become my blade')) 
		assert_that(get_note_ngrams(obj).split(), has_length(30))
		
	def test_note2(self):
		obj = self.note2
		id_str = 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0932:5573657273'
		assert_that(get_id(obj), is_(id_str))
		assert_that(get_oid(obj), is_(id_str))
		assert_that(get_ntiid(obj), is_(id_str))
		assert_that(get_creator(obj), is_('carlos.sanchez@nextthought.com'))
		assert_that(get_keywords(obj), is_([]))
		assert_that(get_sharedWith(obj), is_([]))
		assert_that(get_containerId(obj), is_('tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		# assert_that(get_collectionId(obj), is_('prealgebra'))
		assert_that(get_last_modified(obj), is_(close_to(1334000544.120455, 0.05)))
		assert_that(get_note_content(obj), is_('eddard stark lord of winterfell')) 
		assert_that(get_note_ngrams(obj).split(), has_length(17))
		
	def test_messageinfo(self):
		obj = self.messageinfo
		oid_str = 'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73'
		assert_that(get_id(obj), is_('0d7ba380e77241508204a9d737625e04'))
		assert_that(get_oid(obj), is_(oid_str))
		assert_that(get_ntiid(obj), is_(oid_str))
		assert_that(get_creator(obj), is_('troy.daley@nextthought.com'))
		assert_that(get_keywords(obj), is_([]))
		assert_that(get_channel(obj), is_('DEFAULT'))
		assert_that(get_sharedWith(obj), is_([u'troy.daley@nextthought.com', u'carlos.sanchez@nextthought.com']))
		assert_that(get_containerId(obj), is_('tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x82:53657373696f6e73'))
		# assert_that(get_collectionId(obj), is_('prealgebra'))
		assert_that(get_last_modified(obj), is_(close_to(1321391468.41, 0.05)))
		assert_that(get_messageinfo_content(obj), is_('zanpakuto and zangetsu')) 
		assert_that(get_messageinfo_ngrams(obj).split(), has_length(13))
		
	def _externalize(self, clazz, data, query):
		d = _provide_highlight_snippet(clazz(data), query)
		return toExternalObject(d)
		
	def test_get_index_hit_from_hightlight(self):
		d = self._externalize(_HighlightSearchHit, self.hightlight, 'divide')
		assert_that(d, has_entry(CLASS, HIT))
		# assert_that(d, has_entry(COLLECTION_ID, 'prealgebra'))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(d, has_entry(CREATOR, u'carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'))
		assert_that(d, has_entry(TARGET_OID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'))
		assert_that(d,
			has_entry(SNIPPET, u'You know how to add subtract multiply and DIVIDE In fact you may already know how to solve many of the problems'))
		
	def test_get_index_hit_from_note(self):
		d = self._externalize(_NoteSearchHit, self.note, 'waves')
		assert_that(d, has_entry(CLASS, HIT))
		# assert_that(d, has_entry(COLLECTION_ID, 'prealgebra'))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(d, has_entry(CREATOR, u'carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0860:5573657273'))
		assert_that(d, has_entry(TARGET_OID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0860:5573657273'))
		assert_that(d, has_entry(SNIPPET, u'All WAVES Rise now and Become my Shield Lightning Strike now and'))
		
	def test_get_index_hit_from_messgeinfo(self):
		d = self._externalize(_MessageInfoSearchHit, self.messageinfo, '')
		assert_that(d, has_entry(CLASS, HIT))
		# assert_that(d, has_entry(COLLECTION_ID, 'prealgebra'))
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
