#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from whoosh import fields
from whoosh.filedb.filestore import RamStorage

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._whoosh_query import create_query_parser
from nti.contentsearch._whoosh_query import CosineScorerModel as CSM

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import ConfiguringTestBase

from nti.contentsearch.tests import zanpakuto_commands

from hamcrest import (assert_that, close_to)

class TestWhooshQuery(ConfiguringTestBase):

	schema = fields.Schema(	docid = fields.ID(stored=True, unique=True),
							content = fields.TEXT(stored=True))
			
	def _create_user(self, ds=None, username='nt@nti.com', password='temp001'):
		ds = ds or mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
	
	def _create_ds_note(self, user, text):
		note = Note()
		note.creator = user.username
		note.body = [unicode(text)]
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		mock_dataserver.current_transaction.add(note)
		note = user.addContainedObject( note )
		return note
	
	@WithMockDSTrans
	def test_cosine_scorer(self):
		
		user = self._create_user()
		rim = search_interfaces.IRepozeEntityIndexManager(user, None)
					
		idx = RamStorage().create_index(self.schema)
		writer = idx.writer()
		for n, x in enumerate(zanpakuto_commands):
			writer.add_document(docid = unicode(n), content = unicode(x))
			note = self._create_ds_note(user, x)
			rim.index_content(note)
		writer.commit()

		with idx.searcher(weighting=CSM) as s:
			qp = create_query_parser(u'content', self.schema)
			hits = s.search(qp.parse(u"shield"), limit=len(zanpakuto_commands))
			whoosh_score = hits[0].score
		
		results = rim.search("shield")
		repoze_score = results[0].score
		
		assert_that(repoze_score, close_to(whoosh_score, 0.05))
