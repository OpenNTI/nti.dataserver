#!/usr/bin/env python
from __future__ import print_function

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import simplejson

from zope import interface

from nti.appserver.link_providers import flag_link_provider

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.externalization import to_json_representation

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, is_, has_length, has_entry)

class TestCoppaAdminViews(SharedApplicationTestBase):

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
			
	@WithSharedApplicationMockDS
	def test_upgrade_preflight_coppa_user(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			interface.alsoProvides(u, nti_interfaces.ICoppaUser)

		testapp = TestApp(self.app)

		path = '/dataserver2/users/sjohnson@nextthought.com/@@upgrade_preflight_coppa_user'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'
		
		data = to_json_representation( {'Username': 'aizen@nt.com',
										'birthdate': '2007-11-30',
										'realname': 'Aizen',
										'email': 'aizen@bleach.com',} )
		
		testapp.post(path, data, extra_environ=environ)
