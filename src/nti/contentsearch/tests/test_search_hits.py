#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that

import os
import json
import time

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Highlight
from nti.dataserver.contenttypes import Redaction

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import update_from_external_object

from .. import search_hits
from ..common import get_type_name
from ..content_types import BookContent
from .. import interfaces as search_interfaces

from ..constants import (NTIID, CREATOR, CONTAINER_ID, CLASS, TYPE, HIT, SNIPPET)

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

class TestSearchHits(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestSearchHits, cls).setUpClass()
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

	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	def _externalize(self, clazz, data, query):
		d = clazz(data)
		d.Query = search_interfaces.ISearchQuery(query)
		return toExternalObject(d)

	def test_get_type_name(self):
		assert_that(get_type_name(self.note), is_('note'))
		assert_that(get_type_name(self.hightlight), is_('highlight'))
		assert_that(get_type_name(self.messageinfo), is_('messageinfo'))

	def test_get_search_hit(self):
		hit = search_hits.get_search_hit({})
		assert_that(hit, is_not(None))

	def test_search_hit_hightlight_dict(self):
		d = self._externalize(search_hits._HighlightSearchHit, self.hightlight, 'divide')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(d, has_entry(CREATOR, u'carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x085a:5573657273'))
		assert_that(d, has_entry(SNIPPET,
								 u'You know how to add, subtract, multiply, and divide. In fact, you may already know how to solve many of the problems'))

	def test_seach_hit_redaction_dict(self):
		d = self._externalize(search_hits._RedactionSearchHit, self.redaction, '')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:AOPS-HTML-Howes_converted.0'))
		assert_that(d, has_entry(CREATOR, u'carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x1876:5573657273'))
		assert_that(d, has_entry(SNIPPET, u'serving a sentence in a Michigan jail'))

	def test_search_hit_note_dict(self):
		d = self._externalize(search_hits._NoteSearchHit, self.note, 'waves')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.0'))
		assert_that(d, has_entry(CREATOR, u'carlos.sanchez@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:carlos.sanchez@nextthought.com-OID-0x0860:5573657273'))
		assert_that(d, has_entry(SNIPPET, u'All Waves, Rise now and Become my Shield, Lightning, Strike now and'))

	def test_search_hit_messgeinfo_dict(self):
		d = self._externalize(search_hits._MessageInfoSearchHit, self.messageinfo, '')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x82:53657373696f6e73'))
		assert_that(d, has_entry(CREATOR, u'troy.daley@nextthought.com'))
		assert_that(d, has_entry(NTIID, u'tag:nextthought.com,2011-10:zope.security.management.system_user-OID-0x8a:53657373696f6e73'))
		assert_that(d, has_entry(SNIPPET, u'Zanpakuto and Zangetsu'))

	@WithMockDSTrans
	def test_search_hit_note_ds(self):
		usr = self._create_user()
		note = Note()
		note.body = [u'It is not enough to mean well, we actually have to do well']
		note.creator = usr.username
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		mock_dataserver.current_transaction.add(note)
		note = usr.addContainedObject(note)
		oidstr = to_external_ntiid_oid(note)
		d = self._externalize(search_hits._NoteSearchHit, note, 'well')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(TYPE, 'Note'))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(d, has_entry(CREATOR, u'nt@nti.com'))
		assert_that(d, has_entry(NTIID, oidstr))
		assert_that(d, has_entry(SNIPPET, u'It is not enough to mean well, we actually have to do well'))

	@WithMockDSTrans
	def test_search_hit_hightlight_ds(self):
		usr = self._create_user()
		highlight = Highlight()
		highlight.selectedText = u'Kon saw it! The Secret of a Beautiful Office Lady'
		highlight.creator = usr.username
		highlight.containerId = make_ntiid(nttype='bleach', specific='manga')
		highlight = usr.addContainedObject(highlight)
		oidstr = to_external_ntiid_oid(highlight)
		d = self._externalize(search_hits._HighlightSearchHit, highlight, 'secret')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(TYPE, 'Highlight'))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(d, has_entry(CREATOR, u'nt@nti.com'))
		assert_that(d, has_entry(NTIID, oidstr))
		assert_that(d, has_entry(SNIPPET, u'Kon saw it! The Secret of a Beautiful Office Lady'))

	@WithMockDSTrans
	def test_search_hit_redaction_ds(self):
		usr = self._create_user()
		redaction = Redaction()
		redaction.selectedText = u'Fear'
		update_from_external_object(redaction, {'replacementContent': u'redaction',
												'redactionExplanation': u'Have overcome it everytime I have been on the verge of death'})
		redaction.creator = usr.username
		redaction.containerId = make_ntiid(nttype='bleach', specific='manga')
		redaction = usr.addContainedObject(redaction)
		oidstr = to_external_ntiid_oid(redaction)
		d = self._externalize(search_hits._RedactionSearchHit, redaction, 'death')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(TYPE, 'Redaction'))
		assert_that(d, has_entry(CONTAINER_ID, u'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(d, has_entry(CREATOR, u'nt@nti.com'))
		assert_that(d, has_entry(NTIID, oidstr))
		assert_that(d, has_entry(SNIPPET, u'overcome it everytime I have been on the verge of death'))

	def test_search_hit_book(self):
		containerId = make_ntiid(nttype='bleach', specific='manga')
		hit = BookContent()
		hit.docnum = 100
		hit.title = 'Bleach'
		hit.ntiid = containerId
		hit.last_modified = time.time()
		hit.content = u'All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'
		d = self._externalize(search_hits._WhooshBookSearchHit, hit, 'shield')
		assert_that(d, has_entry(CLASS, HIT))
		assert_that(d, has_entry(TYPE, 'Content'))
		assert_that(d, has_entry(CONTAINER_ID, containerId))
		assert_that(d, has_entry(NTIID, containerId))
		assert_that(d, has_entry(SNIPPET, u'All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))
