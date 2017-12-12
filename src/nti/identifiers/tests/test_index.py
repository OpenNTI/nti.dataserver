#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder

from zope import component

from zope.intid.interfaces import IIntIds

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.users.users import User

from nti.identifiers.index import get_identifier_catalog

from nti.identifiers.utils import get_user_for_external_id
from nti.identifiers.utils import get_external_ids_for_user

from nti.identifiers.interfaces import IUserExternalIdentityContainer


class TestIndex(DataserverLayerTest):

    @WithMockDSTrans
    def test_index(self):
        """
        Validate the index contains the correct external_ids for users.
        """
        # pylint: disable=too-many-function-args
        user1 = User.create_user(self.ds, username="marko")
        catalog = get_identifier_catalog()
        assert_that(catalog, not_none())
        intids = component.getUtility(IIntIds)
        id_container = IUserExternalIdentityContainer(user1)
        assert_that(id_container, has_length(0))
        catalog.index_doc(intids.getId(user1), user1)

        # Empty cases
        assert_that(get_user_for_external_id('type', None), none())
        assert_that(get_user_for_external_id(None, 'dneusername'), none())
        assert_that(get_user_for_external_id('type', 'dneusername'), none())

        # Actual cases
        user2 = User.create_user(self.ds, username="ghuus")
        user3 = User.create_user(self.ds, username="izabel")

        # One user with data
        id_container1 = IUserExternalIdentityContainer(user1)
        id_container1.add_external_mapping('TYPE1', 'ID1')
        catalog.index_doc(intids.getId(user1), user1)
        assert_that(get_user_for_external_id('type1', 'id1'), is_(user1))
        assert_that(get_user_for_external_id('TYPE1', 'ID1'), is_(user1))

        assert_that(get_user_for_external_id('TYPE1xxx', 'ID1'), none())
        assert_that(get_user_for_external_id('TYPE1', 'ID1xxx'), none())

        # Two users
        id_container1.add_external_mapping('TYPE2', 'ID2')
        id_container2 = IUserExternalIdentityContainer(user2)
        id_container2.add_external_mapping('TYPE2', 'ID1')
        catalog.index_doc(intids.getId(user1), user1)
        catalog.index_doc(intids.getId(user2), user2)
        catalog.index_doc(intids.getId(user3), user3)

        assert_that(get_user_for_external_id('type1', 'id1'), is_(user1))
        assert_that(get_user_for_external_id('type2', 'id1'), is_(user2))
        assert_that(get_user_for_external_id('type1', 'id2'), none())

        assert_that(get_user_for_external_id('TYPE1xxx', 'ID1'), none())
        assert_that(get_user_for_external_id('TYPE1', 'ID1xxx'), none())

        external_ids = get_external_ids_for_user(user1)
        assert_that(external_ids, contains_inanyorder('id1', 'id2'))
        external_ids = get_external_ids_for_user(user2)
        assert_that(external_ids, contains_inanyorder('id1'))
        external_ids = get_external_ids_for_user(user3)
        assert_that(external_ids, has_length(0))
