#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,no-member,too-many-public-methods

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to

from zope import interface

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.webtest import TestApp

from nti.app.users.utils import set_user_creation_site

from nti.dataserver.interfaces import ICoppaUserWithAgreementUpgraded

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IUserContactProfile

from nti.dataserver.users.users import User


class TestApplicationUserProfileViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test_user_info_extract(self):
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(external_value={'email': u"nti@nt.com",
                                                     'realname': u'steve johnson',
                                                     'alias': u'citadel'})
            set_user_creation_site(user, 'mathcounts.nextthought.com')
            self._create_user(username=u'rukia@nt.com',
                              external_value={'email': u'rukia@nt.com',
                                              'realname': u'rukia foo',
                                              'alias': u'sode no shirayuki'})
            self._create_user(username=u'ichigo@nt.com',
                              external_value={'email': u'ichigo@nt.com',
                                              'realname': u'イチゴ Kurosaki',
                                              'alias': u'zangetsu'})

        testapp = TestApp(self.app)

        path = '/dataserver2/@@user_info_extract'
        environ = self._make_extra_environ()
        environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'

        res = testapp.get(path, extra_environ=environ,
                          headers={'accept': 'text/csv'})
        assert_that(res.status_int, is_(200))
        app_iter = res.app_iter[0].split('\n')[:-1]
        assert_that(app_iter, has_length(2))
        for t in app_iter:
            assert_that(t.split(','), has_length(7))

        all_sites_path = '/dataserver2/@@user_info_extract?all_sites=True'
        environ = self._make_extra_environ()
        environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'

        res = testapp.get(all_sites_path,
                          extra_environ=environ,
                          headers={'accept': 'text/csv'})
        assert_that(res.status_int, is_(200))
        app_iter = res.app_iter[0].split('\n')[:-1]
        assert_that(app_iter, has_length(4))
        for t in app_iter:
            assert_that(t.split(','), has_length(7))

        res = testapp.get(path, extra_environ=environ,
                          headers={'accept': 'application/json'})
        items = res.json_body['Items']
        assert_that(items, has_length(1))

        res = testapp.get(all_sites_path,
                          extra_environ=environ,
                          headers={'accept': 'application/json'})
        items = res.json_body['Items']
        assert_that(items, has_length(3))

    @WithSharedApplicationMockDS
    def test_inactive_accounts(self):
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(external_value={'email': u"nti@nt.com",
                                              'realname': u'steve johnson'})
            self._create_user(username=u'rukia@nt.com',
                              external_value={'email': u'rukia@nt.com',
                                              'realname': u'rukia foo'})
            self._create_user(username=u'ichigo@nt.com',
                              external_value={'email': u'ichigo@nt.com',
                                              'realname': u'ichigo kurosaki'})
        testapp = TestApp(self.app)

        path = '/dataserver2/@@inactive_accounts'
        environ = self._make_extra_environ()
        environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'

        res = testapp.get(path, extra_environ=environ)
        assert_that(res.status_int, is_(200))
        app_iter = res.app_iter[0].split('\n')[:-1]
        assert_that(app_iter, has_length(4))
        for t in app_iter:
            assert_that(t.split(','), has_length(6))

    @WithSharedApplicationMockDS
    def test_opt_in_comm(self):
        with mock_dataserver.mock_db_trans(self.ds):
            u = self._create_user(external_value={'email': u"nti@nt.com",
                                                  'opt_in_email_communication': True})
            interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

            u = self._create_user(username=u'rukia@nt.com',
                                  external_value={'email': u'rukia@nt.com',
                                                  'opt_in_email_communication': True})
            interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

            u = self._create_user(username=u'ichigo@nt.com',
                                  external_value={'email': u'ichigo@nt.com',
                                                  'opt_in_email_communication': True})
            interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

        testapp = TestApp(self.app)

        path = '/dataserver2/@@user_opt_in_comm'
        environ = self._make_extra_environ()
        environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'

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
            u = self._create_user(external_value={'email': u"nti@nt.com",
                                                  'email_verified': True})
            interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

            u = self._create_user(username=u'rukia@nt.com',
                                  external_value={'email': u'rukia@nt.com',
                                                  'email_verified': True})
            interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

            u = self._create_user(username=u'ichigo@nt.com',
                                  external_value={'email': u'ichigo@nt.com',
                                                  'email_verified': True})
            interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

        testapp = TestApp(self.app)

        path = '/dataserver2/@@user_email_verified'
        environ = self._make_extra_environ()
        environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'

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
            u = self._create_user(external_value={'email': u"nti@nt.com",
                                                  'opt_in_email_communication': True})
            interface.alsoProvides(u, ICoppaUserWithAgreementUpgraded)

            u = self._create_user(username=u'ichigo@nt.com',
                                  external_value={'email': u'ichigo@nt.com',
                                                  'opt_in_email_communication': True})

        testapp = TestApp(self.app)

        path = '/dataserver2/@@user_profile_info'
        environ = self._make_extra_environ()
        environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'

        res = testapp.get(path, extra_environ=environ)
        assert_that(res.status_int, is_(200))
        app_iter = res.app_iter[0].split('\n')[:-1]
        assert_that(app_iter, has_length(3))

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_update_profile(self):
        with mock_dataserver.mock_db_trans(self.ds):
            u = self._create_user(username=u'ichigo@nt.com',
                                  external_value={'email': u"ichigo@nt.com",
                                                  'alias': u'foo'})
            assert_that(IFriendlyNamed(u), has_property('alias', 'foo'))

        post_data = {
            'username': 'ichigo@nt.com',
            'alias': 'Ichigo',
            'phones': {'home': '+81-90-1790-1357'},
        }
        path = '/dataserver2/@@user_profile_update'
        res = self.testapp.put_json(path, post_data, status=200)

        assert_that(res.json_body,
                    has_entry('Allowed Fields',
                              has_length(greater_than_or_equal_to(12))))
        assert_that(res.json_body,
                    has_entry('External', has_entry('alias', 'Ichigo')))
        assert_that(res.json_body,
                    has_entry('Profile', 'CompleteUserProfile'))
        assert_that(res.json_body,
                    has_entry('Summary', has_entry('alias', 'Ichigo')))

        with mock_dataserver.mock_db_trans(self.ds):
            u = User.get_user('ichigo@nt.com')
            assert_that(IFriendlyNamed(u), has_property('alias', 'Ichigo'))
            assert_that(IUserContactProfile(u),
                        has_property('phones', has_entry('home', '+81-90-1790-1357')))

        path = '/dataserver2/users/ichigo@nt.com/@@phones'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body,
                    has_entry('Items', has_entry('home', '+81-90-1790-1357')))

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_update_addresses(self):
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=u'ichigo@nt.com',
                              external_value={'email': u"ichigo@nt.com",
                                              'alias': u'foo'})

        path = '/dataserver2/users/ichigo@nt.com/@@addresses'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body,
                    has_entry('Items', has_length(0)))

        post_data = {
            'home': {'city': 'Karakura Town',
                     'country': 'Japan',
                     'state': 'Chiyoda',
                     'postal_code': '100-0001',
                     'full_name': 'Kurosaki Ichigo',
                     'street_address_1': 'Kurosaki Clinic',
                     'street_address_2': u'クロサキ医院'}
        }
        self.testapp.put_json(path, post_data, status=200)

        res = self.testapp.get(path, status=200)
        assert_that(res.json_body,
                    has_entry('Items',
                              has_entry('home', has_entries('street_address_2', u'クロサキ医院',
                                                            'postal_code', '100-0001',
                                                            'full_name', 'Kurosaki Ichigo',))))
        
    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_update_emails(self):
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=u'ichigo@nt.com',
                              external_value={'email': u"ichigo@nt.com",
                                              'alias': u'foo'})

        path = '/dataserver2/users/ichigo@nt.com/@@contact_emails'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body,
                    has_entry('Items', has_length(0)))

        post_data = {
            'home': 'ichigo@'
        }
        self.testapp.put_json(path, post_data, status=422)

        post_data = {
            'work': 'ichigo@bleach.org',
            'home': 'ichigo@kurosaki.com'
        }
        self.testapp.put_json(path, post_data, status=200)
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body,
                    has_entry('Items',
                              has_entries('home', 'ichigo@kurosaki.com',
                                          'work', 'ichigo@bleach.org')))
