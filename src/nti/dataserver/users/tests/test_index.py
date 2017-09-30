#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users.communities import Community

from nti.dataserver.users.index import create_entity_catalog

from nti.dataserver.users.users import User

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


class TestEntityIndex(DataserverLayerTest):

    def _fixture(self):
        user = User(username=u"ichigo@bleach.org", password=u'temp001')
        user.updateFromExternalObject(
            {'realname': u'Ichigo Kurosaki',
             'alias' : u'Ichigo',
             'email': u"ichigo@bleach.org"}
        )
        community = Community(username=u'bleach')
        return user, community

    #@WithMockDSTrans
    def test_index(self):
        user, community =  self._fixture()
        catalog = create_entity_catalog()
        catalog.index_doc(1, user)
        catalog.index_doc(2, community)

        for name, query in ( ('alias', 'Ichigo'), 
                             ('realname', 'Ichigo Kurosaki'),
                             ('email', 'ichigo@bleach.org'),
                             ('mimeType', 'application/vnd.nextthought.user')):
            index = catalog[name]
            results = index.apply((query,query))
            assert_that(results, has_length(1))

        is_community_idx = catalog['topics']['is_community']
        assert_that(list(is_community_idx.ids()),
                    has_length(1))
