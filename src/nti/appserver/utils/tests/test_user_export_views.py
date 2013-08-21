#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import simplejson

from io import BytesIO
from zope import interface

from nti.dataserver.contenttypes import Note
from nti.dataserver import interfaces as nti_interfaces

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, is_, has_length, has_entry, greater_than)

class TestApplicationUserExporViews(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_user_info_extract(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(external_value={u'email':u"nti@nt.com", u'realname':u'steve',
											  u'alias':u'citadel'})
			self._create_user(username='rukia@nt.com',
							  external_value={u'email':u'rukia@nt.com', u'realname':u'rukia',
											  u'alias':u'sode no shirayuki'})
			self._create_user(username='ichigo@nt.com',
							  external_value={u'email':u'ichigo@nt.com', u'realname':u'ichigo',
											  u'alias':u'zangetsu'})
		testapp = TestApp(self.app)

		path = '/dataserver2/@@user_info_extract'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		app_iter = res.app_iter[0].split('\n')[:-1]
		assert_that(app_iter, has_length(4))
		for t in app_iter:
			assert_that(t.split(','), has_length(4))

	@WithSharedApplicationMockDS
	def test_opt_in_comm(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user(external_value={u'email':u"nti@nt.com", u'opt_in_email_communication':True})
			interface.alsoProvides(u, nti_interfaces.ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='rukia@nt.com',
								  external_value={u'email':u'rukia@nt.com', u'opt_in_email_communication':True})
			interface.alsoProvides(u, nti_interfaces.ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='ichigo@nt.com',
								  external_value={u'email':u'ichigo@nt.com', u'opt_in_email_communication':True})
			interface.alsoProvides(u, nti_interfaces.ICoppaUserWithAgreementUpgraded)

		testapp = TestApp(self.app)

		path = '/dataserver2/@@user_opt_in_comm'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		app_iter = res.app_iter[0].split('\n')[:-1]
		assert_that(app_iter, has_length(4))
		for idx, t in enumerate(app_iter):
			split = t.split(',')
			assert_that(split, has_length(6))
			if idx > 0:
				assert_that(split[-1], is_('True'))

	@WithSharedApplicationMockDS
	def test_profile_info(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user(external_value={u'email':u"nti@nt.com", u'opt_in_email_communication':True})
			interface.alsoProvides(u, nti_interfaces.ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='ichigo@nt.com',
								  external_value={u'email':u'ichigo@nt.com', u'opt_in_email_communication':True})

		testapp = TestApp(self.app)

		path = '/dataserver2/@@user_profile_info'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		app_iter = res.app_iter[0].split('\n')[:-1]
		assert_that(app_iter, has_length(3))

	@WithSharedApplicationMockDS
	def test_export_user_objects(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(external_value={u'email':u"nti@nt.com", u'opt_in_email_communication':True})
			note = Note()
			note.body = [u'bankai']
			note.creator = user
			note.containerId = u'mycontainer'
			note = user.addContainedObject(note)

		testapp = TestApp(self.app)
		environ = self._make_extra_environ()
		path = '/dataserver2/@@export_user_objects'
		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		assert_that(res.headers, has_entry('Content-Length', greater_than(500)))
		stream = BytesIO(res.body)
		stream.seek(0)
		d = simplejson.load(stream)
		assert_that(d, has_entry(u'body', [u'bankai']))
		
	@WithSharedApplicationMockDS
	def test_delete_user_objects(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(external_value={u'email':u"nti@nt.com", u'opt_in_email_communication':True})
			note = Note()
			note.body = [u'bankai']
			note.creator = user
			note.containerId = u'mycontainer'
			note = user.addContainedObject(note)

		testapp = TestApp(self.app)
		environ = self._make_extra_environ()
		path = '/dataserver2/@@delete_user_objects'
		res = testapp.post(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		d = simplejson.loads(res.body)
		assert_that(d, has_entry(u"application/vnd.nextthought.note", 1))

	@WithSharedApplicationMockDS
	def test_ghost_containers(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(external_value={u'email':u"nti@nt.com", u'opt_in_email_communication':True})
			username = user.username
			note = Note()
			note.body = [u'bankai']
			note.creator = user
			note.containerId = u'mycontainer'
			note = user.addContainedObject(note)

		testapp = TestApp(self.app)
		environ = self._make_extra_environ()
		path = '/dataserver2/@@user_ghost_containers'
		res = testapp.get(path, params={"usernames":username}, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		stream = BytesIO(res.body)
		stream.seek(0)
		result = simplejson.load(stream)
		assert_that(result, has_length(1))
		assert_that(result, has_entry('sjohnson@nextthought.com', has_length(1)))
		assert_that(result['sjohnson@nextthought.com'], has_entry('mycontainer', 1))
