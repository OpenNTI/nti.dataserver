#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from hamcrest import assert_that
from hamcrest import is_

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.users.utils import is_email_valid
from nti.dataserver.users.utils import is_email_verified

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestSubscribers(DataserverLayerTest):

    @WithMockDSTrans
    def test_email_verification(self):
        user = User.create_user(username=u'foobar', password=u'bar001', external_value={'email': u'foo@bar.com'})
        assert_that(is_email_verified(u'foo@bar.com'), is_(False))

        profile = IUserProfile(user)
        profile.email_verified = True
        assert_that(is_email_verified(u'foo@bar.com'), is_(True))

    @WithMockDSTrans
    def test_email_validation(self):
        user = User.create_user(username=u'foobar', password=u'bar001', external_value={'email': u'foo@bar.com'})
        assert_that(is_email_valid(u'foo@bar.com'), is_(True))

        profile = IUserProfile(user)
        profile.email_verified = True
        assert_that(is_email_valid(u'foo@bar.com'), is_(True))

        profile.email_verified = False
        assert_that(is_email_valid(u'foo@bar.com'), is_(False))
