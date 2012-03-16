import os
import json
import unittest

from nti.contentsearch._repoze_index import get_id
from nti.contentsearch._repoze_index import get_oid
from nti.contentsearch._repoze_index import get_ntiid
from nti.contentsearch._repoze_index import get_creator
from nti.contentsearch._repoze_index import get_keywords
from nti.contentsearch._repoze_index import get_sharedWith
from nti.contentsearch._repoze_index import get_containerId
from nti.contentsearch._repoze_index import get_collectionId
from nti.contentsearch._repoze_index import get_last_modified
from nti.contentsearch._repoze_index import get_highlight_ngrams
from nti.contentsearch._repoze_index import get_highlight_content
from nti.contentsearch._repoze_index import create_notes_catalog
from nti.contentsearch._repoze_index import create_highlight_catalog
from nti.contentsearch._repoze_index import create_messageinfo_catalog
	
from hamcrest import assert_that
from hamcrest import close_to
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import greater_than_or_equal_to

from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										COLLECTION_ID, SNIPPET, HIT, ID, BODY)

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_,
										recipients_, sharedWith_, body_, startHighlightedFullText_)


class TestRepozeIndex(unittest.TestCase):
		
	def _test_common_catalog(self, catalog):
		assert_that(catalog, has_key(OID))
		assert_that(catalog, has_key(NTIID))
		assert_that(catalog, has_key(CREATOR))
		assert_that(catalog, has_key(keywords_))
		assert_that(catalog, has_key(sharedWith_))
		assert_that(catalog, has_key(CONTAINER_ID))
		assert_that(catalog, has_key(COLLECTION_ID))
		assert_that(catalog, has_key(LAST_MODIFIED))
		
	def teste_notes_catalog(self):
		catalog = create_notes_catalog()
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(references_))
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))
		
	def teste_highlight_catalog(self):
		catalog = create_highlight_catalog()
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))
	
	def teste_messageinf_catalog(self):
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
		tf = os.path.join(os.path.dirname(__file__), 'highlight.json')
		with open(tf, "r") as f:
			obj = json.load(f)
		
		id_str = 'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'
		assert_that(get_id(obj), is_(id_str))
		assert_that(get_oid(obj), is_(id_str))
		assert_that(get_ntiid(obj), is_(id_str))
		assert_that(get_creator(obj), is_('carlos.sanchez@nextthought.com'))
		assert_that(get_keywords(obj), is_(None))
		assert_that(get_sharedWith(obj), is_(None))
		assert_that(get_containerId(obj), is_('tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(get_collectionId(obj), is_('prealgebra'))
		assert_that(get_last_modified(obj), is_(close_to(1331922120.97, 0.05)))
		assert_that(get_highlight_content(obj), has_length(greater_than_or_equal_to(190)))
		
if __name__ == '__main__':
	unittest.main()
