#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_string
does_not = is_not

import fudge

import simplejson as json

from webob.cookies import parse_cookie

from zope import lifecycleevent

from zope.event import notify

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.users.utils import set_user_creation_site

from nti.dataserver.tests import mock_dataserver

from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.identifiers.interfaces import IUserExternalIdentityContainer


class TestListViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    @fudge.patch('nti.app.users.views.list_views.get_component_hierarchy_names')
    def test_list_users(self, mock_sites):
        mock_sites.is_callable().returns(("bleach.org",))

        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(username=u'steve@nt.com',
                                     external_value={'email': u"steve@nt.com",
                                                     'realname': u'steve johnson',
                                                     'alias': u'citadel'})
            set_user_creation_site(user, "nt.com")
            lifecycleevent.modified(user)

            user = self._create_user(username=u'rukia@bleach.com',
                                     external_value={'email': u'rukia@bleach.com',
                                                     'realname': u'rukia kuchiki',
                                                     'alias': u'sode no shirayuki'})
            set_user_creation_site(user, "bleach.org")
            lifecycleevent.modified(user)

            user = self._create_user(username=u'ichigo@bleach.com',
                                     external_value={'email': u'ichigo@bleach.com',
                                                     'realname': u'ichigo kurosaki',
                                                     'alias': u'zangetsu'})
            set_user_creation_site(user, "bleach.org")
            lifecycleevent.modified(user)

            user = self._create_user(username=u'aizen@bleach.com',
                                     external_value={'email': u'newemail@gmail.com',
                                                     'realname': u'aizen sosuke',
                                                     'alias': u'kyoka suigetsu'})
            set_user_creation_site(user, "bleach.org")
            lifecycleevent.modified(user)
            identity_container = IUserExternalIdentityContainer(user)
            identity_container.add_external_mapping('ext id1', 'aaaaaaa')
            notify(ObjectModifiedFromExternalEvent(user))

        url = '/dataserver2/users/@@site_users'
        self.testapp.get(url,
                         extra_environ=self._make_extra_environ(username='steve@nt.com'),
                         status=401)

        params = {"site": 'othersite.com'}
        self.testapp.get(url, params, status=422)

        params = {"site": 'bleach.org', 'sortOn': 'createdTime'}
        res = self.testapp.get(url, params, status=200)
        assert_that(res.json_body, has_entry('Total', is_(3)))
        assert_that(res.json_body, has_entry('Items', has_length(3)))

        params = {"site": 'bleach.org', 'searchTerm': 'ichi'}
        res = self.testapp.get(url, params, status=200)
        assert_that(res.json_body, has_entry('Total', is_(1)))
        assert_that(res.json_body, has_entry('Items', has_length(1)))
        
        params = {"site": 'bleach.org', 'searchTerm': 'newemail'}
        res = self.testapp.get(url, params, status=200)
        assert_that(res.json_body, has_entry('Total', is_(1)))
        assert_that(res.json_body, has_entry('Items', has_length(1)))
        assert_that(res.json_body['Items'][0], has_entry('email', 'newemail@gmail.com'))
        
        # CSV
        params = {"site": 'bleach.org', 'sortOn': 'createdTime'}
        headers = {'accept': str('text/csv')}
        
        # Call without download-token param works
        self.testapp.get(url, params, status=200, headers=headers)
        # As does call with empty string
        params['download-token'] = ''
        self.testapp.get(url, params, status=200, headers=headers)
        params['download-token'] = 1234
        res = self.testapp.get(url, params, status=200, headers=headers)
        cookies = dict(parse_cookie(res.headers['Set-Cookie']))
        assert_that(cookies, has_item('download-1234'))
        cookie_res = json.loads(cookies['download-1234'])
        assert_that(cookie_res, has_entry('success', True))
        
        assert_that(res.body, contains_string('username,realname,alias,email,createdTime,lastLoginTime,ext id1'))
        assert_that(res.body, contains_string('aaaaaa'))
        
        res = self.testapp.post('%s?format=text/csv&site=bleach.org&sortOn=createdTime' % url)
        assert_that(res.body, contains_string('username,realname,alias,email,createdTime,lastLoginTime,ext id1'))
        assert_that(res.body, contains_string('aaaaaa'))
        
        usernames = {'usernames': ['rukia@bleach.com', 'steve@nt.com', 'dneusername']}
        res = self.testapp.post_json('%s?format=text/csv&site=bleach.org&sortOn=createdTime' % url,
                                     usernames)
        assert_that(res.body, contains_string('username,realname,alias,email,createdTime,lastLoginTime'))
        assert_that(res.body, does_not(contains_string('ext id1')))
        assert_that(res.body, does_not(contains_string('aaaaaa')))
        assert_that(res.body, does_not(contains_string('dneusername')))
        assert_that(res.body, does_not(contains_string('ichigo@bleach.com')))
        assert_that(res.body, contains_string('ukia@bleach.com'))
        assert_that(res.body, does_not(contains_string('steve@nt.com')))
        
        res = self.testapp.post('%s?format=text/csv&site=bleach.org&sortOn=createdTime' % url,
                                params=usernames,
                                content_type='application/x-www-form-urlencoded')
        assert_that(res.body, contains_string('username,realname,alias,email,createdTime,lastLoginTime'))
        assert_that(res.body, does_not(contains_string('ext id1')))
        assert_that(res.body, does_not(contains_string('aaaaaa')))
        assert_that(res.body, does_not(contains_string('dneusername')))
        assert_that(res.body, does_not(contains_string('ichigo@bleach.com')))
        assert_that(res.body, contains_string('ukia@bleach.com'))
        assert_that(res.body, does_not(contains_string('steve@nt.com')))
