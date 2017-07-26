#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder

import unittest

from zope import component
from zope import interface

from nti.dataserver.interfaces import IUser

from nti.dataserver.users import User

from nti.identifiers.index import get_identifier_catalog

from nti.identifiers.utils import get_user_for_external_id
from nti.identifiers.utils import get_external_ids_for_user

from nti.identifiers.interfaces import IExternalIdentifierUtility

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import mock_db_trans

class BaseTestExternalIdentifierUtility(object):

    TYPE = None

    def __init__(self, *args):
        pass

    def get_namespaced_external_id(self, user):
        return '%s_site_%s' % (self.TYPE, user.username)

@component.adapter(IUser)
@interface.implementer(IExternalIdentifierUtility)
class TestExternalIdentifierUtilityA(BaseTestExternalIdentifierUtility):

    TYPE = "TYPEA"

@component.adapter(IUser)
@interface.implementer(IExternalIdentifierUtility)
class TestExternalIdentifierUtilityB(BaseTestExternalIdentifierUtility):

    TYPE = "TYPEB"

class TestIndex(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDS
    def test_index(self):
        """
        Validate the index contains the correct external_ids for users.
        """
        with mock_db_trans():
            User.create_user(self.ds, username="marko")
        with mock_db_trans():
            catalog = get_identifier_catalog()
            assert_that( catalog, not_none() )

            user = User.get_user('marko')
            external_ids = get_external_ids_for_user(user)
            assert_that(external_ids, has_length(0))

            # Empty case
            assert_that(get_user_for_external_id(None), none())
            assert_that(get_user_for_external_id('dneusername'), none())


        # Register utility
        with mock_db_trans():
            try:
                component.getGlobalSiteManager()
                component.provideSubscriptionAdapter(TestExternalIdentifierUtilityA,
                                                     adapts=(IUser,))
                component.provideSubscriptionAdapter(TestExternalIdentifierUtilityB,
                                                     adapts=(IUser,))

                user = User.create_user(self.ds, username="alana")
                external_ids = get_external_ids_for_user(user)
                assert_that(external_ids, contains_inanyorder('TYPEA_site_alana'.lower(),
                                                              'TYPEB_site_alana'.lower()))

                found_user = get_user_for_external_id('TYPEA_site_alana')
                assert_that(found_user, is_(user))
                found_user = get_user_for_external_id('TYPEB_site_alana')
                assert_that(found_user, is_(user))
                found_user = get_user_for_external_id('typeb_site_alana')
                assert_that(found_user, is_(user))
            finally:
                gsm = component.getGlobalSiteManager()
                gsm.unregisterSubscriptionAdapter(TestExternalIdentifierUtilityA)
                gsm.unregisterSubscriptionAdapter(TestExternalIdentifierUtilityB)

