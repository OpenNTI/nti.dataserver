import os
import shutil
import unittest
import tempfile

from zope import component
from ZODB import DB
from ZODB.FileStorage import FileStorage

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.ntiids import make_ntiid

from nti.contentsearch._repoze_datastore import DataStore	
from nti.contentsearch._repoze_userindexmanager import RepozeUserIndexManager	

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans, MockDataserver, current_mock_ds
from nti.dataserver.tests.mock_dataserver import ConfiguringTestBase

from nti.contentsearch.common import ( 	HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS, SNIPPET, 
										NTIID, OID)

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

_phrases = ("Shoot To Kill",
			"Bloom, Split and Deviate",
			"Rankle the Seas and the Skies",
			"Lightning Flash Flame Shell",
			"Flower Wind Rage and Flower God Roar, Heavenly Wind Rage and Heavenly Demon Sneer",
			"All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade", 
			"Cry, Raise Your Head, Rain Without end.",
			"Sting All Enemies To Death",
			"Reduce All Creation to Ash",
			"Sit Upon the Frozen Heavens", 
			"Call forth the Twilight")

class TestRepozeUserIndexManager(ConfiguringTestBase):
		
	def setUp(self):
		ConfiguringTestBase.setUp(self)
		self.db_dir = tempfile.mkdtemp(dir="/tmp")
		self.storage = FileStorage(os.path.join(self.db_dir, 'data.fs'))
		self.db = DB(self.storage) 
		self.repoze = DataStore(self.db)
			
	def tearDown(self):
		ConfiguringTestBase.tearDown(self)
		self.repoze.close()
		shutil.rmtree(self.db_dir, True)

	def _add_notes(self, usr=None, conn=None):
		notes = []
		conn = conn or current_mock_ds
		usr = usr or User( 'nt@nti.com', 'temp' )
		for x in _phrases:
			note = Note()
			note.body = [unicode(x)]
			note.creator = usr.username
			note.containerId = make_ntiid(nttype='bleach', specific='manga')
			if conn: conn.add(note)
			notes.append(usr.addContainedObject( note ))	
		return notes, usr
	
	def _index_notes(self, dataserver=None, usr=None, conn=None, do_assert=True):
		docids = []
		notes, usr = self._add_notes(usr=usr, conn=conn)
		rim = RepozeUserIndexManager ( usr.username, self.repoze, dataserver)
		for note in notes:		
			teo = note.toExternalObject()
			docid = rim.index_content(teo)
			if do_assert: assert_that(docid, is_not(None))
			docids.append(docids)
		return notes, docids, rim
			
	@WithMockDSTrans
	def test_index_notes(self):
		self._index_notes()
		
	def test_query_notes(self):
		ds = MockDataserver()
		component.provideUtility( ds )
		try:
			with ds.dbTrans() as ct:
				usr = User( 'nt@nti.com', 'temp' )
				ds.root['users']['nt@nti.com'] = usr
				_, _, rim = self._index_notes(dataserver=ds, usr=usr, conn=ct, do_assert=False)
				
			hits = rim.search("shield", limit=None)
			assert_that(hits, has_entry(HIT_COUNT, 1))
			assert_that(hits, has_entry(QUERY, 'shield'))
			assert_that(hits, has_key(ITEMS))
			
			items = hits[ITEMS]
			assert_that(items, has_length(1))
			
			key = list(items.keys())[0]
			assert_that(items[key], has_entry(CLASS, HIT))
			assert_that(items[key], has_entry(NTIID, is_not(None)))
			assert_that(items[key], has_entry(OID, is_not(None)))
			assert_that(key, is_(items[key][NTIID]))
			assert_that(items[key], has_entry(CONTAINER_ID, 'tag:nextthought.com,2011-10:bleach-manga'))
			assert_that(items[key], has_entry(SNIPPET, 'All Waves Rise now and Become my SHIELD Lightning Strike now and Become my Blade'))
		finally:
			ds.close()
			assert component.getGlobalSiteManager().unregisterUtility( ds ) or component.getSiteManager().unregisterUtility( ds )
		
if __name__ == '__main__':
	unittest.main()
