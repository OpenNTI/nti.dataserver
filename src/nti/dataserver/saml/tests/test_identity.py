#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

from nti.dataserver.saml.interfaces import ISAMLIDPUserInfoBindings

from nti.dataserver.users.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer


class TestIdentity(DataserverLayerTest):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_adapter(self):
        user = User.create_user(self.ds, username=u'ichigo@bleach.org')
        bindings = ISAMLIDPUserInfoBindings(user, None)
        assert_that(bindings, is_not(none()))
