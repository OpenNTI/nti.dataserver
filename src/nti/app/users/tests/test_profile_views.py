#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
from hamcrest.library.number.ordering_comparison import greater_than_or_equal_to
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from zope import interface

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.interfaces import ICoppaUserWithAgreementUpgraded

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.webtest import TestApp
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestApplicationUserProfileViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_user_info_extract(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(external_value={u'email':u"nti@nt.com",
											  u'realname':u'steve johnson',
											  u'alias':u'citadel'})
			self._create_user(username='rukia@nt.com',
							  external_value={u'email':u'rukia@nt.com',
											  u'realname':u'rukia foo',
											  u'alias':u'sode no shirayuki'})
			self._create_user(username='ichigo@nt.com',
							  external_value={u'email':u'ichigo@nt.com',
											  u'realname':u'ichigo bar',
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
			assert_that(t.split(','), has_length(7))

	@WithSharedApplicationMockDS
	def test_inactive_accounts(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user(external_value={u'email':u"nti@nt.com",
											  u'realname':u'steve johnson'})
			self._create_user(username='rukia@nt.com',
							  external_value={u'email':u'rukia@nt.com',
											  u'realname':u'rukia foo'})
			self._create_user(username='ichigo@nt.com',
							  external_value={u'email':u'ichigo@nt.com',
											  u'realname':u'ichigo kurosaki'})
		testapp = TestApp(self.app)

		path = '/dataserver2/@@inactive_accounts'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		app_iter = res.app_iter[0].split('\n')[:-1]
		assert_that(app_iter, has_length(4))
		for t in app_iter:
			assert_that(t.split(','), has_length(6))

	@WithSharedApplicationMockDS
	def test_opt_in_comm(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user(external_value={u'email':u"nti@nt.com",
												  u'opt_in_email_communication':True})
			interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='rukia@nt.com',
								  external_value={u'email':u'rukia@nt.com',
												  u'opt_in_email_communication':True})
			interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='ichigo@nt.com',
								  external_value={u'email':u'ichigo@nt.com',
												  u'opt_in_email_communication':True})
			interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

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
			assert_that(split, has_length(7))
			if idx > 0:
				assert_that(split[-1].strip(), is_('True'))

	@WithSharedApplicationMockDS
	def test_emailed_verfied(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user(external_value={u'email':u"nti@nt.com",
												  u'email_verified':True})
			interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='rukia@nt.com',
								  external_value={u'email':u'rukia@nt.com',
												  u'email_verified':True})
			interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='ichigo@nt.com',
								  external_value={u'email':u'ichigo@nt.com',
												  u'email_verified':True})
			interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

		testapp = TestApp(self.app)

		path = '/dataserver2/@@user_email_verified'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		app_iter = res.app_iter[0].split('\n')[:-1]
		assert_that(app_iter, has_length(4))
		for t in app_iter:
			split = t.split(',')
			assert_that(split, has_length(7))

	@WithSharedApplicationMockDS
	def test_profile_info(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user(external_value={u'email':u"nti@nt.com",
												  u'opt_in_email_communication':True})
			interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='ichigo@nt.com',
								  external_value={u'email':u'ichigo@nt.com',
												  u'opt_in_email_communication':True})

		testapp = TestApp(self.app)

		path = '/dataserver2/@@user_profile_info'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		app_iter = res.app_iter[0].split('\n')[:-1]
		assert_that(app_iter, has_length(3))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_update_profile(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user(username='ichigo@nt.com',
							  	  external_value={u'email':u"ichigo@nt.com", u'alias':'foo'})
			assert_that(IFriendlyNamed(u), has_property('alias', 'foo'))

		post_data = {'username':'ichigo@nt.com', 'alias':'Ichigo'}
		path = '/dataserver2/@@user_profile_update'
		res = self.testapp.post_json(path, post_data, status=200)

		assert_that(res.json_body, has_entry('Allowed Fields', has_length(greater_than_or_equal_to(12))))
		assert_that(res.json_body, has_entry('External', has_entry('alias', 'Ichigo')))
		assert_that(res.json_body, has_entry('Profile', u'CompleteUserProfile'))
		assert_that(res.json_body, has_entry('Summary', has_entry('alias', 'Ichigo')))

		with mock_dataserver.mock_db_trans(self.ds):
			u = User.get_user('ichigo@nt.com')
			assert_that(IFriendlyNamed(u), has_property('alias', 'Ichigo'))
