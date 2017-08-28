#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import unittest

from zope import component
from zope import interface

from nti.dataserver.interfaces import IUserBlacklistedStorage

from nti.dataserver.users.interfaces import IRecreatableUser

from nti.dataserver.users.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer


class TestBlackList(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_storage(self):
        storage = component.queryUtility(IUserBlacklistedStorage)
        assert_that(storage, is_not(none()))
        assert_that(storage, validly_provides(IUserBlacklistedStorage))
        assert_that(storage, verifiably_provides(IUserBlacklistedStorage))
        assert_that(storage, has_length(0))

        ichigo = User.create_user(username='ichigo@bleach.org')
        interface.alsoProvides(ichigo, IRecreatableUser)

        User.create_user(username='izuru@bleach.org')
        User.create_user(username='toshiro@bleach.org')

        User.delete_entity('ichigo@bleach.org')
        assert_that(storage, has_length(0))

        User.delete_entity('izuru@bleach.org')
        assert_that(storage, has_length(1))

        assert_that(list(storage), has_length(1))

        User.delete_entity('toshiro@bleach.org')
        assert_that(storage, has_length(2))

        storage.remove('toshiro@bleach.org')
        assert_that(storage, has_length(1))

        storage.clear()
        assert_that(storage, has_length(0))
