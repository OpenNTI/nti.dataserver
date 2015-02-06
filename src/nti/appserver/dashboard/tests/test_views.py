#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

import random
import collections
from urllib import quote
from operator import itemgetter

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.ntiids.ntiids import make_ntiid

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.decorators import WithSharedApplicationMockDSWithChanges

class TestDashboardViews(ApplicationLayerTest):

	def _create_note(self, user, msg, title=None, containerId=None, sharedWith=()):
		note = Note()
		note.updateLastMod()
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
		assert_that(items[1], has_entry('Score', 5))
		assert_that(items[1], has_entry('Total', 1))
		assert_that(items[1], has_entry('Username', u'aizen@nt.com'))
		assert_that(items[2], has_entry('Score', 1))
		assert_that(items[2], has_entry('Total', 1))
		assert_that(items[2], has_entry('Username', u'gin@nt.com'))
		assert_that(items[3], has_entry('Score', 0))
		assert_that(items[3], has_entry('Total', 1))
		assert_that(items[3], has_entry('Username', u'ichigo@nt.com'))

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_unique_minmax_summary_vieww(self):
		requestor = 'ichigo@nt.com'
		containerId = make_ntiid(nttype='bleach', specific='manga')
		with mock_dataserver.mock_db_trans(self.ds):
			ichigo = self._create_user(username='ichigo@nt.com')
			self._create_note(ichigo, "Kamishini no Yari", 'Bankai', containerId)
			self._create_note(ichigo, "kyoka suigetsu", 'Bankai', containerId)
			self._create_note(ichigo, "Sode no Shirayuki", 'Bankai', containerId)
			self._create_note(ichigo, "tensa zangetsu", 'Bankai', containerId)

		testapp = TestApp(self.app)
		path = '/dataserver2/users/%s/Pages(%s)/UniqueMinMaxSummary?attribute=%s' % (requestor, containerId, 'containerId')
		res = testapp.get(str(path), extra_environ=self._make_extra_environ(user=requestor))
		assert_that(res.status_int, is_(200))
		assert_that(res.json_body, has_entry('Total', 1))
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		items = res.json_body['Items']
		assert_that(items[0], has_entry('body', is_([u'tensa zangetsu'])))

	def _create_comment_data_for_POST(self, unique):
		data = { 'Class': 'Post',
				 'title': 'A comment',
				 'body': ['This is a comment body %s ' % unique ] }
		return data

	def _create_post_data_for_POST(self, title, unique=''):
		data = { 'Class': 'Post',
				 'MimeType': 'application/vnd.nextthought.forums.post',
				 'title': title,
				 'description': "This is a description of the thing I'm creating",
				 'body': ['My first thought. %s' % unique] }

		return data

	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_toptopics_view(self):
		forum_pretty_url = quote('/dataserver2/users/Bleach/DiscussionBoard/Forum')
		# board_pretty_url = forum_pretty_url[:-(len(_FORUM_NAME) + 1)]

		usernames = ('aizen@nt.com', 'ichigo@nt.com', 'urahara@nt.com')
		with mock_dataserver.mock_db_trans(self.ds):
			usrlst = []
			for username in usernames:
				user = self._create_user(username=username)
				usrlst.append(user)

			c = users.Community.create_community(self.ds, username='Bleach')
			for u in usrlst:
				u.record_dynamic_membership(c)
				u.follow(c)
			frm_interfaces.ICommunityForum(c)

		locations = collections.defaultdict(int)
		for x in range(random.randint(5, 10)):
			requestor = random.choice(usernames)
			testapp = TestApp(self.app, extra_environ=self._make_extra_environ(user=requestor))
			data = self._create_post_data_for_POST('From %s(%s)' % (requestor, random.random()), str(x))
			res = testapp.post_json(forum_pretty_url, data, status=201)
			locations[res.location] = 0
			publish_url = self.require_link_href_with_rel(res.json_body, u'publish')
			testapp.post_json(publish_url, data, status=200)

		for x in range(random.randint(5, 10)):
			username = random.choice(usernames)
			location = random.choice(locations.keys())
			testapp = TestApp(self.app, extra_environ=self._make_extra_environ(user=username))
			for x in range(random.randint(5, 10)):
				data = self._create_comment_data_for_POST(random.random())
				testapp.post_json(location, data, status=201)
				locations[location] += 1

		username = random.choice(usernames)
		testapp = TestApp(self.app, extra_environ=self._make_extra_environ(user=username))
		res = testapp.get(forum_pretty_url, status=200)
		top_topics = self.require_link_href_with_rel(res.json_body, u'TopTopics')
		res = testapp.get(top_topics, status=200)

		sorted_locations = sorted(locations.items(), key=itemgetter(1), reverse=True)
		data = res.json_body
		assert_that(data, has_entry('Items', has_length(len(locations))))
		items = data['Items']
		x = 0
		for _, count in sorted_locations:
			assert_that(items[x], has_entry('PostCount', count))
			x+=1
