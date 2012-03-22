import os
import json
import time
import shutil
import unittest
import tempfile
from datetime import datetime

from ZODB import DB
from ZODB.FileStorage import FileStorage

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.ntiids import make_ntiid

from nti.contentsearch._whoosh_index import create_book_schema
from nti.contentsearch._whoosh_indexstorage import create_directory_index
from nti.contentsearch._whoosh_bookindexmanager import WhooshBookIndexManager
from nti.contentsearch._repoze_datastore import RepozeDataStore	
from nti.contentsearch._repoze_userindexmanager import RepozeUserIndexManager	

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


from nti.contentsearch.common import ( 	HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET, 
										NTIID, TARGET_OID)

from nti.contentsearch.tests import phrases
from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (is_, is_not, has_key, has_item, has_entry, has_length, assert_that)

class _BaseIndexManagerTest(object):
				
	@classmethod
	def setUpClass(cls):	
		cls.now = time.time()
		cls.idx_dir = tempfile.mkdtemp(dir="/tmp")
			
		path = os.path.join(os.path.dirname(__file__), 'highlight.json')
		with open(path, "r") as f:
			cls.hightlight = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'note.json')
		with open(path, "r") as f:
			cls.note = json.load(f)
			
		path = os.path.join(os.path.dirname(__file__), 'message_info.json')
		with open(path, "r") as f:
			cls.messageinfo = json.load(f)
		
		cls._add_book_data()

	@classmethod
	def _add_book_data(cls):
		cls.now = time.time()
		cls.book_idx_dir = tempfile.mkdtemp(dir="/tmp")
		create_directory_index('bleach', create_book_schema(), cls.book_idx_dir)
		cls.bim = WhooshBookIndexManager('bleach', indexdir=cls.idx_dir) 
		
		idx = cls.bim.bookidx
		writer = idx.writer()
		for x in phrases:
			writer.add_document(ntiid = unicode(make_ntiid(nttype='bleach', specific='manga')),
								title = unicode(x),
								content = unicode(x),
								quick = unicode(x),
								related= u'',
								section= u'',
								last_modified=datetime.fromtimestamp(cls.now))
		writer.commit()
		
	@classmethod
	def tearDownClass(cls):
		cls.bim.close()
		shutil.rmtree(cls.book_idx_dir, True)
		
	
if __name__ == '__main__':
	unittest.main()
