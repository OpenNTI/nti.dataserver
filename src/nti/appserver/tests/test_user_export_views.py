#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from .test_application import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, is_, has_length)

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
