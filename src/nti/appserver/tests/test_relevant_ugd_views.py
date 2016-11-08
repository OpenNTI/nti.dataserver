#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Redaction

from nti.externalization.internalization import update_from_external_object

from nti.ntiids.ntiids import make_ntiid

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDSWithChanges

from nti.appserver.tests import ExLibraryApplicationTestLayer

class TestRelevantUGDView(ApplicationLayerTest):
	layer = ExLibraryApplicationTestLayer

	def _create_note(self, user, msg, title=None, containerId=None, sharedWith=(), inReplyTo=None):
		note = Note()
		note.updateLastMod()
		note.body = [unicode(msg)]
		note.creator = user.username
		note.inReplyTo = inReplyTo
		note.title = IPlainTextContentFragment(title) if title else None
		note.containerId = containerId or make_ntiid(nttype='bleach', specific='manga')
		with user.updates():
			for st in sharedWith or ():
				note.addSharingTarget(st)
			note = user.addContainedObject(note)
		return note

	def _create_redaction(self, user, selection, content, explanation, containerId=None):
		redaction = Redaction()
		redaction.selectedText = selection
		update_from_external_object(redaction, {'replacementContent': content,
												'redactionExplanation':explanation})
		redaction.creator = user
		redaction.containerId = containerId or  make_ntiid(nttype='bleach', specific='manga')
		redaction = user.addContainedObject(redaction)

	@WithSharedApplicationMockDSWithChanges
	@fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
	def test_relevant_view(self, mock_interaction):
		mock_interaction.is_callable().with_args().returns(True)
		requestor = 'ichigo@nt.com'
		containerId = 'tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.brief_history_of_cosmetology'
		sub_container_id = "tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.1920s"
		with mock_dataserver.mock_db_trans(self.ds):

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
			bankai.creator = unohana # Creator must be set
			unohana.addContainedObject(bankai)
			bankai.addFriend(ichigo)
			bankai.addFriend(urahara)

			self._create_note(ichigo, "tensa zangetsu", 'Bankai', containerId)
			self._create_note(gin, "Kamishini no Yari", 'Bankai', containerId, sharedWith=(ichigo,))
			self._create_note(rukia, "Sode no Shirayuki", 'Bankai', containerId, sharedWith=(c,))
			kyoka = self._create_note(aizen, "kyoka suigetsu", 'Bankai', containerId, sharedWith=(bankai,))
			self._create_note(gin, "Kanzen Saimin", 'Bankai', containerId, sharedWith=(ichigo,), inReplyTo=kyoka)
			# Sub container
			self._create_note(gin, "Kamishini no Yari", 'Bankai', sub_container_id, sharedWith=(ichigo,))
			self._create_note(rukia, "Sode no Shirayuki", 'Bankai', sub_container_id, sharedWith=(c,))
			kyoka = self._create_note(aizen, "kyoka suigetsu", 'Bankai', sub_container_id, sharedWith=(bankai,))

			self._create_redaction(ichigo, 'Fear', 'Zangetsu Gone', 'The Asauchi breaks away to reveal Hollow Ichigo', containerId)
			self._create_redaction(rukia, 'Fear', 'Zangetsu Gone', 'The Asauchi breaks away to reveal Hollow Ichigo', containerId)

		# Our recursive call finds everything
		testapp = TestApp(self.app)
		path = '/dataserver2/users/%s/Pages(%s)/RelevantUserGeneratedData' % (requestor, containerId)
		res = testapp.get(str(path), extra_environ=self._make_extra_environ(user=requestor))
		assert_that(res.status_int, is_(200))
		assert_that(res.json_body, has_entry('Total', 8))
		assert_that(res.json_body, has_entry('Items', has_length(8)))

		# Our contained call returns everything but subcontainer ugd.
		path = '/dataserver2/users/%s/Pages(%s)/RelevantContainedUserGeneratedData' % (requestor, containerId)
		res = testapp.get(str(path), extra_environ=self._make_extra_environ(user=requestor))
		assert_that(res.status_int, is_(200))
		assert_that(res.json_body, has_entry('Total', 5))
		assert_that(res.json_body, has_entry('Items', has_length(5)))

	@WithSharedApplicationMockDSWithChanges
	def test_relevant_view_quiz(self):
		requestor = 'ichigo@nt.com'
		parent = 'tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.cosmetology'
		containerId = 'tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.1'
		with mock_dataserver.mock_db_trans(self.ds):
			ichigo = self._create_user(username='ichigo@nt.com')
			note = self._create_note(ichigo, "tensa zangetsu", 'Bankai', containerId)
			note.body = [IPlainTextContentFragment("test_relevant_view_quiz")]

		testapp = TestApp(self.app)
		path = '/dataserver2/users/%s/Pages(%s)/RelevantUserGeneratedData' % (requestor, parent)
		res = testapp.get(str(path), extra_environ=self._make_extra_environ(user=requestor))
		assert_that(res.status_int, is_(200))
		assert_that(res.json_body, has_entry('Total', 1))
		assert_that(res.json_body, has_entry('Items', has_length(1)))
