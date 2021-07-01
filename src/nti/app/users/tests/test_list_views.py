#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

import fudge

from zope import lifecycleevent

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.users.utils import set_user_creation_site

from nti.dataserver.tests import mock_dataserver


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

        url = '/dataserver2/users/@@site_users'
        headers = {'accept': str('application/json')}
        self.testapp.get(url,
                         extra_environ=self._make_extra_environ(username='steve@nt.com'),
                         headers=headers,
                         status=401)

        params = {"site": 'othersite.com'}
        self.testapp.get(url, params, status=422)

        params = {"site": 'bleach.org', 'sortOn': 'createdTime'}
        res = self.testapp.get(url, params, status=200, headers=headers)
        assert_that(res.json_body, has_entry('Total', is_(3)))
        assert_that(res.json_body, has_entry('Items', has_length(3)))

        params = {"site": 'bleach.org', 'searchTerm': 'ichi'}
        res = self.testapp.get(url, params, status=200, headers=headers)
        assert_that(res.json_body, has_entry('Total', is_(1)))
        assert_that(res.json_body, has_entry('Items', has_length(1)))
        
        params = {"site": 'bleach.org', 'searchTerm': 'newemail'}
        res = self.testapp.get(url, params, status=200, headers=headers)
        assert_that(res.json_body, has_entry('Total', is_(1)))
        assert_that(res.json_body, has_entry('Items', has_length(1)))
        assert_that(res.json_body['Items'][0], has_entry('email', 'newemail@gmail.com'))
