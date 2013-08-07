#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver import users
from nti.dataserver.contenttypes import Note

from nti.ntiids.ntiids import make_ntiid

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDSWithChanges

from hamcrest import (assert_that, is_, has_length, has_entry)

class TestDashboardViews(SharedApplicationTestBase):

	def _create_note(self, user, msg, title=None, containerId=None, sharedWith=()):
		note = Note()
		note.body = [unicode(msg)]
		note.creator = user.username
		note.title = IPlainTextContentFragment(title) if title else None
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		with user.updates():
			for st in sharedWith or ():
				note.addSharingTarget(st)
			note = user.addContainedObject(note)
		return note

	@WithSharedApplicationMockDSWithChanges
	def test_top_user_summary_view(self):
		requestor = 'ichigo@nt.com'
		containerId = make_ntiid(nttype='bleach', specific='manga')
		with mock_dataserver.mock_db_trans(self.ds):
			self.ds.add_change_listener(users.onChange)

			gin = self._create_user(username='gin@nt.com')
			aizen = self._create_user(username='aizen@nt.com')
			rukia = self._create_user(username='rukia@nt.com')
			ichigo = self._create_user(username='ichigo@nt.com')
			unohana = self._create_user(username='unohana@nt.com')
			urahara = self._create_user(username='urahara@nt.com')

			c = users.Community.create_community(self.ds, username='Bleach')
			for u in (gin, rukia, ichigo, aizen, unohana):
				u.record_dynamic_membership(c)
				u.follow(c)

			bankai = users.DynamicFriendsList(username='bankai')
			bankai.creator = ichigo  # Creator must be set
			ichigo.addContainedObject(bankai)
			bankai.addFriend(unohana)
			bankai.addFriend(urahara)

			self._create_note(ichigo, "tensa zangetsu", 'Bankai', containerId)
			self._create_note(gin, "Kamishini no Yari", 'Bankai', containerId, sharedWith=(ichigo,))
			self._create_note(aizen, "kyoka suigetsu", 'Bankai', containerId, sharedWith=(bankai,))
			self._create_note(rukia, "Sode no Shirayuki", 'Bankai', containerId, sharedWith=(c,))

		testapp = TestApp(self.app)
		path = '/dataserver2/users/%s/Pages(%s)/TopUserSummaryData' % (requestor, containerId)
		res = testapp.get(str(path), extra_environ=self._make_extra_environ(user=requestor))
		assert_that(res.status_int, is_(200))
		assert_that(res.json_body, has_entry('Total', 4))
		assert_that(res.json_body, has_entry('Items', has_length(4)))
		assert_that(res.json_body, has_entry('Summary', has_entry(u'application/vnd.nextthought.note', 4)))
		items = res.json_body.get('Items')
		assert_that(items[0], has_entry('Score', 10))
		assert_that(items[0], has_entry('Total', 1))
		assert_that(items[0], has_entry('Username', u'rukia@nt.com'))
		assert_that(items[1], has_entry('Score', 8))
		assert_that(items[1], has_entry('Total', 1))
		assert_that(items[1], has_entry('Username', u'aizen@nt.com'))
		assert_that(items[2], has_entry('Score', 1))
		assert_that(items[2], has_entry('Total', 1))
		assert_that(items[2], has_entry('Username', u'gin@nt.com'))
		assert_that(items[3], has_entry('Score', 0))
		assert_that(items[3], has_entry('Total', 1))
		assert_that(items[3], has_entry('Username', u'ichigo@nt.com'))
