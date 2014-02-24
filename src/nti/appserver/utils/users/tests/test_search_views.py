#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import greater_than

import simplejson

from nti.contentsearch import interfaces as search_interfaces

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import to_json_representation


from nti.dataserver.tests import mock_dataserver

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.webtest import TestApp

zanpakuto_commands = (
						"Shoot To Kill",
					  	"Bloom, Split and Deviate",
						"Rankle the Seas and the Skies",
						"Lightning Flash Flame Shell",
						"Flower Wind Rage and Flower God Roar, Heavenly Wind Rage and Heavenly Demon Sneer",
						"All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade",
						"Cry, Raise Your Head, Rain Without end",
						"Sting All Enemies To Death",
						"Reduce All Creation to Ash",
						"Sit Upon the Frozen Heavens",
						"Call forth the Twilight"
					  )

class TestApplicationUserExporViews(ApplicationLayerTest):

	def _create_note(self, msg, owner, containerId=None, sharedWith=()):
		note = Note()
		note.creator = owner
		note.body = [unicode(msg)]
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		for s in sharedWith or ():
			note.addSharingTarget(s)
		mock_dataserver.current_transaction.add(note)
		note = owner.addContainedObject(note)
		return note

	def _create_notes(self, usr=None, sharedWith=()):
		notes = []
		for msg in zanpakuto_commands:
			note = self._create_note(msg, usr, sharedWith=sharedWith)
			notes.append(note)
		return notes, usr

	@WithSharedApplicationMockDS
	def test_reindex_content(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			username = u.username
			self._create_notes(u)

		testapp = TestApp(self.app)

		path = '/dataserver2/@@reindex_content'
		environ = self._make_extra_environ()

		res = testapp.post(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		result = simplejson.loads(res.body)
		assert_that(result, has_entry('Items', has_entry('application/vnd.nextthought.note', 11)))

		with mock_dataserver.mock_db_trans(self.ds):
			u = User.get_user(username)
			rim = search_interfaces.IRepozeEntityIndexManager(u)
			hits = rim.search("shoot")
			assert_that(hits, has_length(1))

	@WithSharedApplicationMockDS
	def test_reindex_zero_content(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			username = u.username
			self._create_notes(u)

		testapp = TestApp(self.app)

		path = '/dataserver2/@@reindex_content'
		environ = self._make_extra_environ()

		data = to_json_representation({'mimetypes': 'application/vnd.nextthought.highlight'})
		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		result = simplejson.loads(res.body)
		assert_that(result, has_entry('Items', has_length(0)))

		with mock_dataserver.mock_db_trans(self.ds):
			u = User.get_user(username)
			rim = search_interfaces.IRepozeEntityIndexManager(u)
			hits = rim.search("shoot")
			assert_that(hits, has_length(0))

	@WithSharedApplicationMockDS
	def test_reindex_with_mimetype(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			self._create_notes(u)

		testapp = TestApp(self.app)

		path = '/dataserver2/@@reindex_content'
		environ = self._make_extra_environ()

		data = to_json_representation({'mimetypes': 'application/vnd.nextthought.note'})
		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		result = simplejson.loads(res.body)
		assert_that(result, has_entry('Items', has_entry('application/vnd.nextthought.note', 11)))
