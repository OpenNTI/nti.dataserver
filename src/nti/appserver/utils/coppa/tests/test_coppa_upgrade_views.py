#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


import simplejson
from datetime import date

from zope import interface

from nti.appserver.policies import site_policies
from nti.appserver.link_providers import flag_link_provider

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as users_interfaces

from nti.externalization.externalization import to_json_representation

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, is_, has_length, has_entry, has_key)

class TestCoppaUpgradeViews(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_rollback(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			u = self._create_user(username='aizen@nt.com', external_value={u'email':u"nti@nt.com", u'opt_in_email_communication':True})
			interface.alsoProvides(u, nti_interfaces.ICoppaUser)
			interface.alsoProvides(u, nti_interfaces.ICoppaUserWithAgreementUpgraded)

			u = self._create_user(username='rukia@nt.com',
								  external_value={u'email':u'rukia@nt.com', u'opt_in_email_communication':True})
			interface.alsoProvides(u, nti_interfaces.ICoppaUser)
			interface.alsoProvides(u, nti_interfaces.ICoppaUserWithoutAgreement)

			u = self._create_user(username='ichigo@nt.com',
								  external_value={u'email':u'ichigo@nt.com', u'opt_in_email_communication':True})
			interface.alsoProvides(u, nti_interfaces.ICoppaUser)
			interface.alsoProvides(u, nti_interfaces.ICoppaUserWithAgreement)

			u = self._create_user(username='kuchiki@nt.com',
								  external_value={u'email':u'kuchiki@nt.com', u'opt_in_email_communication':True})
			interface.alsoProvides(u, site_policies.IMathcountsUser)
			interface.alsoProvides(u, site_policies.IMathcountsCoppaUserWithAgreementUpgraded)

			u = self._create_user(username='kenpachi@nt.com',
								  external_value={u'email':u'kenpachi@nt.com', u'opt_in_email_communication':True})
			interface.alsoProvides(u, site_policies.IMathcountsUser)
			interface.alsoProvides(u, site_policies.IMathcountsCoppaUserWithAgreement)

		testapp = TestApp(self.app)

		path = '/dataserver2/@@rollback_coppa_users'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'
		
		res = testapp.post(path,  extra_environ=environ)
		assert_that(res.status_int, is_(200))
		body = simplejson.loads(res.body)
		assert_that(body, has_entry('Count', 3))
		assert_that(body, has_entry('Items', has_length(3)))
		
		with mock_dataserver.mock_db_trans(self.ds):
			u = users.User.get_user('aizen@nt.com')
			assert_that(flag_link_provider.has_link(u, 'coppa.upgraded.rollbacked'), is_(True))
			
			u = users.User.get_user('rukia@nt.com')
			assert_that(flag_link_provider.has_link(u, 'coppa.upgraded.rollbacked'), is_(True))

			u = users.User.get_user('ichigo@nt.com')
			assert_that(flag_link_provider.has_link(u, 'coppa.upgraded.rollbacked'), is_(False))

			u = users.User.get_user('kenpachi@nt.com')
			assert_that(flag_link_provider.has_link(u, 'coppa.upgraded.rollbacked'), is_(False))

	@WithSharedApplicationMockDS
	def test_upgrade_preflight_coppa_user_under_13(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			interface.alsoProvides(u, nti_interfaces.ICoppaUser)

		testapp = TestApp(self.app)

		path = '/dataserver2/users/sjohnson@nextthought.com/@@upgrade_preflight_coppa_user'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		data = to_json_representation({'Username': 'sjohnson@nextthought.com',
									   'birthdate': '2007-11-30',
									   'realname': 'Aizen',
									   'contact_email': 'aizen@bleach.com', })

		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		body = simplejson.loads(res.body)
		assert_that(body, has_entry('Username', 'sjohnson@nextthought.com'))
		assert_that(body, has_entry('ProfileSchema', has_key('birthdate')))
		assert_that(body, has_entry('ProfileSchema', has_key('contact_email')))

	@WithSharedApplicationMockDS
	def test_upgrade_preflight_coppa_user_over_13(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			interface.alsoProvides(u, nti_interfaces.ICoppaUser)

		testapp = TestApp(self.app)

		path = '/dataserver2/users/sjohnson@nextthought.com/@@upgrade_preflight_coppa_user'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'
		
		data = to_json_representation({'Username': 'sjohnson@nextthought.com',
									   'birthdate': '1973-11-30',
									   'realname': 'Aizen Sosuke',
									   'email': 'aizen@bleach.com' })
		
		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		body = simplejson.loads(res.body)
		assert_that(body, has_entry('Username', 'sjohnson@nextthought.com'))
		assert_that(body, has_entry('ProfileSchema', has_key('birthdate')))
		assert_that(body, has_entry('ProfileSchema', has_key('email')))
		assert_that(body, has_entry('ProfileSchema', has_key('realname')))

	@WithSharedApplicationMockDS
	def test_upgrade_coppa_user_over_13(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			interface.alsoProvides(u, site_policies.IMathcountsUser)
			interface.alsoProvides(u, site_policies.IMathcountsCoppaUserWithoutAgreement)
			flag_link_provider.add_link(u, 'coppa.upgraded.rollbacked')

		testapp = TestApp(self.app)

		path = '/dataserver2/users/sjohnson@nextthought.com/@@upgrade_coppa_user'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		data = to_json_representation({'Username': 'sjohnson@nextthought.com',
									   'birthdate': '1973-11-30',
									   'realname': 'Aizen Sosuke',
									   'email': 'aizen@bleach.com', })

		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(204))

		with mock_dataserver.mock_db_trans(self.ds):
			u = users.User.get_user('sjohnson@nextthought.com')
			assert_that(site_policies.IMathcountsUser.providedBy(u), is_(True))
			assert_that(site_policies.IMathcountsCoppaUserWithoutAgreement.providedBy(u), is_(False))
			assert_that(site_policies.IMathcountsCoppaUserWithAgreementUpgraded.providedBy(u), is_(True))
			profile = users_interfaces.IUserProfile(u)
			assert_that(profile.email, is_('aizen@bleach.com'))
			assert_that(flag_link_provider.has_link(u, 'coppa.upgraded.rollbacked'), is_(False))

	@WithSharedApplicationMockDS
	def test_upgrade_coppa_user_under_13(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			interface.alsoProvides(u, site_policies.IMathcountsUser)
			interface.alsoProvides(u, site_policies.IMathcountsCoppaUserWithoutAgreement)
			flag_link_provider.add_link(u, 'coppa.upgraded.rollbacked')

		testapp = TestApp(self.app)

		path = '/dataserver2/users/sjohnson@nextthought.com/@@upgrade_coppa_user'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'

		today = date.today()
		d = date(today.year - 5, today.month, today.day)

		data = to_json_representation({'Username': 'sjohnson@nextthought.com',
									   'birthdate': d.isoformat(),
									   'contact_email': 'aizen@bleach.com', })

		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(204))

		with mock_dataserver.mock_db_trans(self.ds):
			u = users.User.get_user('sjohnson@nextthought.com')
			assert_that(site_policies.IMathcountsUser.providedBy(u), is_(True))
			assert_that(site_policies.IMathcountsCoppaUserWithoutAgreement.providedBy(u), is_(True))
			assert_that(flag_link_provider.has_link(u, 'coppa.upgraded.rollbacked'), is_(False))


