#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import starts_with
from hamcrest import contains_string

from zope import interface

from persistent import Persistent

from nti.app.saml.client import _SAMLNameId

from nti.app.saml.interfaces import ISAMLIDPEntityBindings

from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

from nti.schema.schema import SchemaConfigured

from nti.app.saml.tests import SAMLTestLayer
from nti.app.saml.tests import MockNameId

from nti.app.saml.tests.interfaces import ITestSAMLProviderUserInfo

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


@interface.implementer(ITestSAMLProviderUserInfo)
class TestProviderInfo(SchemaConfigured, Persistent):
    test_id = 'testID1'
    mimeType = mime_type = 'application/vnd.nextthought.saml.testprovideruserinfo'


class TestViews(ApplicationLayerTest):

    layer = SAMLTestLayer

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_provider_info_view_no_user(self):
        ########
        # Setup
        getUrl = "/dataserver2/saml/@@GetProviderUserInfo"

        username = u'bobby.hagen@nextthought.com'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=username)

        extra_environ = self._make_extra_environ(username=username)

        #######
        # Test
        response = self.testapp.get(getUrl,
                                    {},
                                    status=422,
                                    extra_environ=extra_environ)

        #######
        # Verify

        assert_that(str(response), contains_string('Must specify a username.'))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_provider_info_view_no_entity_id(self):
        ########
        # Setup
        getUrl = "/dataserver2/saml/@@GetProviderUserInfo"

        username = b'bobby.hagen@nextthought.com'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=username)

        extra_environ = self._make_extra_environ(username=username)

        #######
        # Test
        response = self.testapp.get(getUrl,
                                    {'user': username},
                                    status=422,
                                    extra_environ=extra_environ)

        #######
        # Verify
        assert_that(str(response), contains_string('Must specify entity_id.'))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_provider_info_view_user_not_found(self):
        ########
        # Setup
        getUrl = "/dataserver2/saml/@@GetProviderUserInfo"

        username = u'bobby.hagen@nextthought.com'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=username)

        extra_environ = self._make_extra_environ(username=username)

        #######
        # Test
        response = self.testapp.get(getUrl,
                                    {'user': 'the.donald@trump.com',
                                     'entity_id': 'test_entity_id'},
                                    status=422,
                                    extra_environ=extra_environ)

        #######
        # Verify

        assert_that(str(response), contains_string('User not found.'))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_provider_info_view_unauthorized(self):

        ########
        # Setup
        getUrl = "/dataserver2/saml/@@GetProviderUserInfo"

        username = u'bobby.hagen@test.com'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=username)

        extra_environ = self._make_extra_environ(username=username)

        #######
        # Test
        self.testapp.get(getUrl,
                         {'user': username, 'entity_id': 'test_entity_id'},
                         status=403,  # FORBIDDEN!!!
                         extra_environ=extra_environ)

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_provider_info_view(self):

        ########
        # Setup
        getUrl = "/dataserver2/saml/@@GetProviderUserInfo"

        username = u'bobby.hagen@nextthought.com'
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(username=username)
            ISAMLIDPUserInfoBindings(user)['test_entity_id'] = TestProviderInfo()

        extra_environ = self._make_extra_environ(username=username)

        #######
        # Test
        response = self.testapp.get(getUrl,
                                    {'user': username, 'entity_id': 'test_entity_id'},
                                    status=200,
                                    extra_environ=extra_environ)

        #######
        # Verify

#         assert_that(str(response), ends_with('Must specify entity_id.'))
        result = response.json_body
        assert_that(result,
                    has_entries({'href': starts_with(getUrl),
                                 'Class': 'TestProviderInfo',
                                 'test_id': 'testID1',
                                 'MimeType': 'application/vnd.nextthought.saml.testprovideruserinfo'
                                 }))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_delete_provider_info_view(self):

        ########
        # Setup
        getUrl = "/dataserver2/saml/@@GetProviderUserInfo"

        admin_user_name = u'bobby.hagen@nextthought.com'
        user_name = u'foo1287'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=admin_user_name)
            user = self._create_user(username=user_name)
            ISAMLIDPUserInfoBindings(user)['test_entity_id'] = TestProviderInfo()

        extra_environ = self._make_extra_environ(username=admin_user_name)

        #######
        # Test
        self.testapp.get(getUrl,
                         {'user': user_name, 'entity_id': 'test_entity_id'},
                         status=200,
                         extra_environ=extra_environ)

        self.testapp.delete("/dataserver2/saml/@@ProviderUserInfo?user=foo1287&entity_id=test_entity_id",
                            status=403,
                            extra_environ=self._make_extra_environ(username=user_name))

        self.testapp.delete("/dataserver2/saml/@@ProviderUserInfo?user=foo1287&entity_id=test_entity_id",
                            status=204,
                            extra_environ=extra_environ)

        self.testapp.get(getUrl,
                         {'user': user_name, 'entity_id': 'test_entity_id'},
                         status=404,
                         extra_environ=extra_environ)

        self.testapp.delete("/dataserver2/saml/@@ProviderUserInfo?user=foo1287&entity_id=test_entity_id",
                            status=404,
                            extra_environ=extra_environ)


class TestNameIdViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_get_for_user(self):
        admin_user = u'chris@nextthought.com'
        username = u'utz2345'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=admin_user)

            user = self._create_user(username=username)
            bindings = ISAMLIDPEntityBindings(user)
            bindings.store_binding(_SAMLNameId(MockNameId('A23BE5')))

        self.testapp.get('/dataserver2/saml/@@NameIds',
                         extra_environ=self._make_extra_environ(username=username),
                         status=403)

        self.testapp.get('/dataserver2/saml/@@NameIds',
                         extra_environ=self._make_extra_environ(username=admin_user),
                         status=422)

        self.testapp.get('/dataserver2/saml/@@NameIds',
                         params={'username': 'idontexist'},
                         extra_environ=self._make_extra_environ(username=admin_user),
                         status=422)

        response = self.testapp.get('/dataserver2/saml/@@NameIds',
                                    {'username': username},
                                    extra_environ=self._make_extra_environ(username=admin_user),
                                    status=200)

        response = response.json_body

        assert_that(response,
                    has_entry('Items', has_entry(starts_with('sso.nt.com'),
                                                 has_entry('nameid', 'A23BE5'))))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_get_for_specific_entity(self):
        admin_user = u'chris@nextthought.com'
        username = u'utz2345'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=admin_user)

            user = self._create_user(username=username)
            bindings = ISAMLIDPEntityBindings(user)
            bindings.store_binding(_SAMLNameId(MockNameId('A23BE5')))

        self.testapp.get('/dataserver2/saml/@@NameIds',
                         params={'username': username,
                                 'name_qualifier': 'sso.nt.com',
                                 'sp_name_qualifier': 'junk'},
                         extra_environ=self._make_extra_environ(
                             username=admin_user),
                         status=404)

        response = self.testapp.get('/dataserver2/saml/@@NameIds',
                                    params={'username': username,
                                            'name_qualifier': 'sso.nt.com',
                                            'sp_name_qualifier': 'sp.nt.com'},
                                    extra_environ=self._make_extra_environ(
                                        username=admin_user),
                                    status=200)

        response = response.json_body

        assert_that(response, has_entry('nameid', 'A23BE5'))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_remove_for_entity(self):
        admin_user = u'chris@nextthought.com'
        username = u'utz2345'
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(username=admin_user)

            user = self._create_user(username=username)
            bindings = ISAMLIDPEntityBindings(user)
            bindings.store_binding(_SAMLNameId(MockNameId('A23BE5')))

        self.testapp.get('/dataserver2/saml/@@NameIds',
                         params={'username': username, 'name_qualifier': 'sso.nt.com',
                                 'sp_name_qualifier': 'sp.nt.com'},
                         extra_environ=self._make_extra_environ(
                             username=admin_user),
                         status=200)

        self.testapp.delete('/dataserver2/saml/@@NameIds?username=utz2345&name_qualifier=sso.nt.com&sp_name_qualifier=sp.nt.com',
                            extra_environ=self._make_extra_environ(
                                username=username),
                            status=403)

        self.testapp.delete('/dataserver2/saml/@@NameIds?username=utz2345&name_qualifier=sso.nt.com&sp_name_qualifier=sp.nt.com',
                            extra_environ=self._make_extra_environ(
                                username=admin_user),
                            status=204)

        self.testapp.get('/dataserver2/saml/@@NameIds',
                         params={'username': username, 'name_qualifier': 'sso.nt.com',
                                 'sp_name_qualifier': 'sp.nt.com'},
                         extra_environ=self._make_extra_environ(
                             username=admin_user),
                         status=404)
