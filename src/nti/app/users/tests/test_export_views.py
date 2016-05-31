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

from urllib import quote

import zc.intid as zc_intid

from zope import component

from nti.chatserver.interfaces import IUserTranscriptStorage

from nti.chatserver.messageinfo import MessageInfo as Msg

from nti.chatserver.meeting import _Meeting as Meet

from nti.dataserver.contenttypes import Note

from nti.dataserver.users import User

from nti.externalization.externalization import to_external_ntiid_oid

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

class TestUserExportViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_export_user_objects(self):

		with mock_dataserver.mock_db_trans(self.ds) as conn:
			user = User.get_user(self.default_username)
			note = Note()
			note.body = [u'bankai']
			note.creator = user
			note.containerId = u'mycontainer'
			note = user.addContainedObject(note)

			storage = IUserTranscriptStorage(user)
			msg = Msg()
			meet = Meet()
			meet.containerId = u'tag:nti:foo'
			meet.creator = user
			meet.ID = 'the_meeting'
			msg.containerId = meet.containerId
			msg.ID = '42'
			msg.creator = user
			msg.__parent__ = meet

			conn.add(msg)
			conn.add(meet)
			component.getUtility(zc_intid.IIntIds).register(msg)
			component.getUtility(zc_intid.IIntIds).register(meet)

			storage.add_message(meet, msg)

		path = '/dataserver2/@@export_user_objects'
		params = {"usernames": self.default_username,
				  "mimeTypes": 'application/vnd.nextthought.note,application/vnd.nextthought.transcript'}
		res = self.testapp.get(path, params, status=200)
		assert_that(res.json_body, has_entry('Total', is_(2)))
		assert_that(res.json_body,
					has_entry('Items',
					 		  has_entry(self.default_username, has_length(2))))

		path = '/dataserver2/@@export_user_objects'
		params = {"usernames": self.default_username,
				  "mimeTypes": 'application/vnd.nextthought.messageinfo'}
		res = self.testapp.get(path, params, status=200)
		assert_that(res.json_body, has_entry('Total', is_(1)))
		assert_that(res.json_body,
					has_entry('Items',
					 		  has_entry(self.default_username, has_length(1))))

		path = '/dataserver2/@@export_user_objects'
		params = {"usernames": self.default_username,
				  "mimeTypes": 'application/vnd.nextthought.note'}
		res = self.testapp.get(path, params, status=200)
		assert_that(res.json_body, has_entry('Total', is_(1)))
		assert_that(res.json_body,
					has_entry('Items',
					 		  has_entry(self.default_username, has_length(1))))

		path = '/dataserver2/@@export_user_objects'
		params = {"usernames": self.default_username}
		res = self.testapp.get(path, params, status=200)
		assert_that(res.json_body, has_entry('Total', is_(2)))
		assert_that(res.json_body,
					has_entry('Items',
					 		  has_entry(self.default_username, has_length(2))))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_export_objects_sharedwith(self):
		with mock_dataserver.mock_db_trans(self.ds):
			steve = User.get_user(self.default_username)

			user = self._create_user(username="troy@nextthought.com",
									 external_value={u'email':u"troy@nt.com",
													 u'opt_in_email_communication':True})
			note = Note()
			note.body = [u'bankai']
			note.creator = steve
			note.addSharingTarget(user)
			note.containerId = u'mycontainer'
			note = steve.addContainedObject(note)

		path = '/dataserver2/@@export_objects_sharedwith'
		params = {"username":"troy@nextthought.com", "mimeTypes":'application/vnd.nextthought.note'}
		res = self.testapp.get(path, params, status=200)
		assert_that(res.json_body, has_entry('Total', is_(1)))
		assert_that(res.json_body, has_entry('Items', has_length(1)))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_export_users(self):

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(username='nti@nt.com',
							  external_value={u'email':u"nti@nt.com",
											  u'realname':u'steve johnson',
											  u'alias':u'citadel'})
			self._create_user(username='rukia@nt.com',
							  external_value={u'email':u'rukia@nt.com',
											  u'realname':u'rukia kuchiki',
											  u'alias':u'sode no shirayuki'})
			self._create_user(username='ichigo@nt.com',
							  external_value={u'email':u'ichigo@nt.com',
											  u'realname':u'ichigo kurosaki',
											  u'alias':u'zangetsu'})
			self._create_user(username='aizen@nt.com',
							  external_value={u'email':u'aizen@nt.com',
											  u'realname':u'aizen sosuke',
											  u'alias':u'kyoka suigetsu'})

		path = '/dataserver2/@@ExportUsers'
		params = {"usernames":'ichigo@nt.com,aizen@nt.com'}
		res = self.testapp.get(path, params, status=200)
		assert_that(res.json_body, has_entry('Total', is_(2)))
		assert_that(res.json_body, has_entry('Items', has_length(2)))

		params = {"usernames":['rukia@nt.com']}
		res = self.testapp.get(path, params, status=200)
		assert_that(res.json_body, has_entry('Total', is_(1)))
		assert_that(res.json_body, has_entry('Items', has_length(1)))

		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Total', is_(0)))
		assert_that(res.json_body, has_entry('Items', has_length(0)))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_object_resolver(self):

		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(self.default_username)
			note = Note()
			note.body = [u'bankai']
			note.creator = user
			note.containerId = u'mycontainer'
			note = user.addContainedObject(note)
			oid = to_external_ntiid_oid(note)

		path = '/dataserver2/@@ObjectResolver/' + quote(oid)
		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Object', has_entry('Class', is_('Note'))))

		path = '/dataserver2/@@ObjectResolver/foo'
		res = self.testapp.get(path, status=404)
