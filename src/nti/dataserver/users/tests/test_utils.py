#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import is_email_verified
from nti.dataserver.users.utils import force_email_verification
from nti.dataserver.users.utils import unindex_email_verification

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer


class TestUtils(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_is_email_verfied(self):
        User.create_user(username=u'ichigo@bleach.org',
                         external_value={'email': u"ichigo@bleach.org",
                                         'email_verified': True})

        User.create_user(username=u'rukia@bleach.org',
                         external_value={'email': u"rukia@bleach.org",
                                         'email_verified': True})
        User.create_user(username=u'foo@bleach.org',
                         external_value={'email': u"foo@bleach.org"})

        assert_that(is_email_verified('ichigo@bleach.org'), is_(True))
        assert_that(is_email_verified('ICHIGO@bleach.ORG'), is_(True))
        assert_that(is_email_verified('rukia@bleach.org'), is_(True))
        assert_that(is_email_verified('foo@bleach.org'), is_(False))
        assert_that(is_email_verified('aizen@bleach.org'), is_(False))

    @WithMockDSTrans
    def test_force_email_verification(self):
        user = User.create_user(username=u'ichigo@bleach.org',
                                external_value={'email': u"ichigo@bleach.org"})

        assert_that(is_email_verified('ichigo@bleach.org'), is_(False))
        force_email_verification(user)
        assert_that(is_email_verified('ichigo@bleach.org'), is_(True))

        unindex_email_verification(user)
        assert_that(is_email_verified('ichigo@bleach.org'), is_(False))
