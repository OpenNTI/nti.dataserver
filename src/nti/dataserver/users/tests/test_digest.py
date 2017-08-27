#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from nti.dataserver.interfaces import IUserDigestEmailMetadata

from nti.dataserver.users.users import User

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer


class TestDigest(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_is_email_verfied(self):
        user = User.create_user(username=u'ichigo@bleach.org')
        meta = IUserDigestEmailMetadata(user, None)
        assert_that(meta, is_not(none()))
        assert_that(meta, has_property('last_sent', is_(0)))
        assert_that(meta, has_property('last_collected', is_(0)))
        meta.last_sent = 100
        meta.last_collected = 80
        assert_that(meta, has_property('last_sent', is_(100)))
        assert_that(meta, has_property('last_collected', is_(80)))
        assert_that(meta, has_length(1))
        User.delete_entity(u'ichigo@bleach.org')
        assert_that(meta, has_length(0))
