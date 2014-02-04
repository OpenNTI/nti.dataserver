#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Redaction
from nti.dataserver.contenttypes.forums.forum import PersonalBlog

from nti.externalization.externalization import toExternalObject
from nti.externalization.internalization import update_from_external_object

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.constants import (tags_)
from nti.contentsearch.constants import (HIT, CLASS, CONTAINER_ID, HIT_COUNT, ITEMS, NTIID,
										 PHRASE_SEARCH, ID, FIELD)

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import ConfiguringTestBase
from nti.contentsearch.tests import zanpakuto_commands

class TestRepozeUserAdapter(ConfiguringTestBase):

	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	def _create_forum(self, user, name='Blog'):
		containers = user.containers
		forum = containers.getContainer(name)
		if forum is None:
			forum = PersonalBlog()
			forum.__parent__ = user
			forum.creator = user
			forum.__name__ = name
			forum.title = user.username
			# TODO: Events?
			containers.addContainer(name, forum, locate=False)
			containers.addContainer(forum.NTIID, forum, locate=False)

	def _create_note(self, msg, username, containerId=None, title=None):
		note = Note()
		if title:
			note.title = IPlainTextContentFragment(title)
		note.body = [unicode(msg)]
		note.creator = username
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		return note

	def _add_notes(self, usr=None, conn=None):
		notes = []
		conn = mock_dataserver.current_transaction
		usr = usr or self._create_user()
		for x in zanpakuto_commands:
			note = self._create_note(x, usr.username)
			if conn: conn.add(note)
			note = usr.addContainedObject(note)
			notes.append(note)
		return notes, usr

	def _index_notes(self, usr=None, do_assert=True):
		docids = []
		notes, usr = self._add_notes(usr=usr)
		rim = search_interfaces.IRepozeEntityIndexManager(usr)
		for note in notes:
			docid = rim.index_content(note)
			if do_assert:
				assert_that(docid, is_not(None))
			docids.append(docid)
		return usr, notes, docids

	def _add_user_index_notes(self):
		usr = self._create_user()
		_, notes, docids = self._index_notes(usr=usr, do_assert=False)
		return usr, docids, notes

	@WithMockDSTrans
	def test_delete_catalog(self):
		usr, _, _, = self._index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		assert_that(rim, has_key('note'))
		rim.remove_index('note')
		assert_that(rim, is_not(has_key('note')))

	@WithMockDSTrans
	def test_query_notes(self):
		usr, _, _ = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)

		results = rim.search("shield")
		hits = toExternalObject(results)
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry('Query', 'shield'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits, has_entry(PHRASE_SEARCH, False))

		items = hits[ITEMS]
		assert_that(items, has_length(1))

		hit = items[0]
		assert_that(hit, has_entry(CLASS, HIT))
		assert_that(hit, has_entry(NTIID, is_not(None)))
		assert_that(hit, has_entry(CONTAINER_ID, 'tag:nextthought.com,2011-10:bleach-manga'))
		assert_that(hit,
					has_entry('Snippet', 'All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))

		hits = rim.search("*")
		assert_that(hits, has_length(0))

		hits = rim.search("?")
		assert_that(hits, has_length(0))

		hits = rim.search("ra*")
		assert_that(hits, has_length(3))

		hits = rim.search('"%s"' % zanpakuto_commands[0])
		assert_that(hits, has_length(1))
		hits = toExternalObject(hits)
		assert_that(hits, has_entry(PHRASE_SEARCH, True))

	@WithMockDSTrans
	def test_update_note(self):
		usr, _, notes = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
		note = notes[5]
		note.body = [u'Blow It Away']
		rim.update_content(note)

		hits = toExternalObject(rim.search("shield"))
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry('Query', 'shield'))

		hits = toExternalObject(rim.search("blow"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry('Query', 'blow'))

	@WithMockDSTrans
	def test_delete_note(self):
		usr, _, notes = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)

		note = notes[5]
		rim.delete_content(note)

		hits = toExternalObject(rim.search("shield"))
		assert_that(hits, has_entry(HIT_COUNT, 0))
		assert_that(hits, has_entry('Query', 'shield'))

	@WithMockDSTrans
	def test_suggest(self):

		usr, _, _ = self._add_user_index_notes()
		rim = search_interfaces.IRepozeEntityIndexManager(usr, None)

		hits = toExternalObject(rim.suggest("ra"))
		assert_that(hits, has_entry(HIT_COUNT, 4))
		assert_that(hits, has_entry('Query', 'ra'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(4))
		assert_that(items, has_item('rankle'))
		assert_that(items, has_item('raise'))
		assert_that(items, has_item('rain'))
		assert_that(items, has_item('rage'))

	@mock_dataserver.WithMockDS
	def test_one_note_index_to_two_users(self):
		ds = mock_dataserver.current_mock_ds
		users = []
		with mock_dataserver.mock_db_trans(ds):
			for x in range(2):
				username = 'nt%s@nti.com' % x
				user = self._create_user(username=username)
				users.append(user)

			note = self._create_note('ichigo', users[0].username)
			note = users[0].addContainedObject(note)

		rims = []
		for x in range(2):
			with mock_dataserver.mock_db_trans(ds):
				usr = users[x]
				rim = search_interfaces.IRepozeEntityIndexManager(usr, None)
				rims.append(rim)
				rim.index_content(note)

		for x in xrange(2):
			with mock_dataserver.mock_db_trans(ds):
				hits = toExternalObject(rims[x].search("ichigo"))
				exp_count = 1 if x == 0 else 0
				assert_that(hits, has_entry(HIT_COUNT, exp_count))

	@WithMockDSTrans
	def test_create_redaction(self):
		username = 'kuchiki@bleach.com'
		user = self._create_user(username=username)
		redaction = Redaction()
		redaction.selectedText = u'Fear'
		update_from_external_object(redaction,
					{'replacementContent': u'Ichigo',
					 'redactionExplanation': u'Have overcome it everytime I have been on the verge of death'})
		redaction.creator = username
		redaction.containerId = make_ntiid(nttype='bleach', specific='manga')
		redaction = user.addContainedObject(redaction)

		rim = search_interfaces.IRepozeEntityIndexManager(user, None)
		docid = rim.index_content(redaction)
		assert_that(docid, is_not(None))

		hits = rim.search("fear")
		assert_that(hits, has_length(1))

		hits = rim.search("death")
		assert_that(hits, has_length(1))

		hits = rim.search("ichigo")
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_note_phrase(self):
		username = 'kuchiki@bleach.com'
		user = self._create_user(username=username)
		msg = u"you'll be ready to rumble"
		note = Note()
		note.body = [unicode(msg)]
		note.creator = username
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		note = user.addContainedObject(note)

		rim = search_interfaces.IRepozeEntityIndexManager(user, None)
		docid = rim.index_content(note)
		assert_that(docid, is_not(None))

		hits = rim.search('"you\'ll be ready"')
		assert_that(hits, has_length(1))

		hits = rim.search('"you will be ready"')
		assert_that(hits, has_length(0))

		hits = rim.search('"Ax+B"')
		assert_that(hits, has_length(0))

	@WithMockDSTrans
	def test_note_math_equation(self):
		username = 'ichigo@bleach.com'
		user = self._create_user(username=username)
		msg = u"ax+by = 100"
		note = Note()
		note.body = [unicode(msg)]
		note.creator = username
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		note = user.addContainedObject(note)

		rim = search_interfaces.IRepozeEntityIndexManager(user, None)
		docid = rim.index_content(note)
		assert_that(docid, is_not(None))

		hits = rim.search('"ax+by"')
		assert_that(hits, has_length(1))

		hits = rim.search('"ax by"')
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_columbia_issue(self):
		username = 'ichigo@bleach.com'
		user = self._create_user(username=username)
		note = Note()
		note.body = [unicode('light a candle')]
		note.creator = username
		note.containerId = make_ntiid(nttype='bleach', specific='manga')
		note = user.addContainedObject(note)

		rim = search_interfaces.IRepozeEntityIndexManager(user, None)
		docid = rim.index_content(note)
		assert_that(docid, is_not(None))

		hits = rim.search('"light a candle"')
		assert_that(hits, has_length(1))

		hits = rim.search("light a candle")
		assert_that(hits, has_length(1))

	@WithMockDSTrans
	def test_title_indexing(self):
		username = 'ichigo@bleach.com'
		user = self._create_user(username=username)
		note = self._create_note(u'The Asauchi breaks away to reveal Hollow Ichigo.', username, title=u'Zangetsu Gone')
		note = user.addContainedObject(note)

		rim = search_interfaces.IRepozeEntityIndexManager(user, None)
		docid = rim.index_content(note)
		assert_that(docid, is_not(None))

		hits = rim.search('Asauchi')
		assert_that(hits, has_length(1))

		hits = rim.search('Zangetsu')
		assert_that(hits, has_length(1))

		rim.delete_content(note)

		hits = rim.search('Asauchi')
		assert_that(hits, has_length(0))

		hits = rim.search('Zangetsu')
		assert_that(hits, has_length(0))

from nti.appserver.tests.test_application import SharedApplicationTestBase
from nti.appserver.tests.test_application import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS

class TestAppRepozeUserAdapter(SharedApplicationTestBase):

	features = SharedApplicationTestBase.features + ('forums',)

	extra_environ_default_user = b'ichigo@bleach.com'

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_post_dict(self):

		data = { 'Class': 'Post',
				 'title': 'Unohana',
				 'body': ["Begging her not to die Kenpachi screams out in rage as his opponent fades away"],
				 'tags': ['yachiru', 'haori'] }

		username = self.extra_environ_default_user
		testapp = self.testapp
		testapp.post_json('/dataserver2/users/%s/Blog' % username, data, status=201)

		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(username)
			rim = search_interfaces.IRepozeEntityIndexManager(user)
			hits = rim.search('Kenpachi')
			assert_that(hits, has_length(1))

			hits = rim.search('Unohana'.upper())
			assert_that(hits, has_length(1))

			hits = rim.search('yachiru')
			assert_that(hits, has_length(1))
			hits = toExternalObject(hits)
			assert_that(hits, has_key(ITEMS))
			items = hits[ITEMS]
			assert_that(items, has_length(1))
			hit = items[0]
			assert_that(hit, has_entry(ID, 'Unohana'))
			assert_that(hit, has_entry(FIELD, tags_))

			hits = rim.search('yachiru'.upper())
			assert_that(hits, has_length(1))

