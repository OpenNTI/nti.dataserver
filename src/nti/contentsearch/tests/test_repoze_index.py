import unittest

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import _repoze_index
from nti.contentsearch._repoze_index import get_object_content

from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, COLLECTION_ID, ID)
from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_,
										recipients_, sharedWith_, replacementContent_, redactionExplanation_)

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from hamcrest import (assert_that, has_key )

_repoze_index.compute_ngrams = True

@unittest.skip
class TestRepozeIndex(ConfiguringTestBase):
			
	def _test_common_catalog(self, catalog):
		assert_that(catalog, has_key(OID))
		assert_that(catalog, has_key(NTIID))
		assert_that(catalog, has_key(CREATOR))
		assert_that(catalog, has_key(keywords_))
		assert_that(catalog, has_key(sharedWith_))
		assert_that(catalog, has_key(CONTAINER_ID))
		assert_that(catalog, has_key(COLLECTION_ID))
		assert_that(catalog, has_key(LAST_MODIFIED))
		
	def test_notes_catalog(self):
		catalog = {}
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(references_))
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))
		
	def test_highlight_catalog(self):
		catalog = {}
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))
		
	def test_redaction_catalog(self):
		catalog = {}
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))
		assert_that(catalog, has_key(replacementContent_))
		assert_that(catalog, has_key(redactionExplanation_))
	
	def test_messageinf_catalog(self):
		catalog = {}
		self._test_common_catalog(catalog)
		assert_that(catalog, has_key(ID))
		assert_that(catalog, has_key(channel_))
		assert_that(catalog, has_key(recipients_))
		assert_that(catalog, has_key(references_))
		assert_that(catalog, has_key(ngrams_))
		assert_that(catalog, has_key(content_))

	@WithMockDSTrans
	def test_note_content(self):
		note = Note()
		note.body = [u'I Think Therefore I Am']
		note.creator = 'nt@nti.com'
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		usr = User.create_user( mock_dataserver.current_mock_ds, username='nt@nti.com', password='temp' )
		mock_dataserver.current_transaction.add(note)
		note = usr.addContainedObject( note ) 
		assert_that(get_object_content(note), 'i think therefore i am')
		#assert_that(get_note_ngrams(note), 'the ther there theref therefo therefor therefore thi thin think')
	
if __name__ == '__main__':
	unittest.main()
