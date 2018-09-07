#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,too-many-function-args

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from six.moves.urllib_parse import quote

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.contenttypes import Note

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.users import User

from nti.ntiids.oids import to_external_ntiid_oid


class TestUserExportViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_export_users(self):

        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=u'nti@nt.com',
                              external_value={'email': u"nti@nt.com",
                                              'realname': u'steve johnson',
                                              'alias': u'citadel'})
            self._create_user(username=u'rukia@nt.com',
                              external_value={'email': u'rukia@nt.com',
                                              'realname': u'rukia kuchiki',
                                              'alias': u'sode no shirayuki'})
            self._create_user(username=u'ichigo@nt.com',
                              external_value={'email': u'ichigo@nt.com',
                                              'realname': u'ichigo kurosaki',
                                              'alias': u'zangetsu'})
            self._create_user(username=u'aizen@nt.com',
                              external_value={'email': u'aizen@nt.com',
                                              'realname': u'aizen sosuke',
                                              'alias': u'kyoka suigetsu'})

        path = '/dataserver2/@@ExportUsers'
        params = {"usernames": 'ichigo@nt.com,aizen@nt.com'}
        res = self.testapp.get(path, params, status=200)
        assert_that(res.json_body, has_entry('Total', is_(2)))
        assert_that(res.json_body, has_entry('Items', has_length(2)))

        params = {"usernames": ['rukia@nt.com']}
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
        assert_that(res.json_body,
                    has_entry('Object', has_entry('Class', is_('Note'))))

        path = '/dataserver2/@@ObjectResolver/foo'
        self.testapp.get(path, status=404)
