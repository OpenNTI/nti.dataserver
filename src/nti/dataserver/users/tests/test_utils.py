#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,too-many-function-args

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

import unittest

from zope import lifecycleevent

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.communities import Community

from nti.dataserver.users.users import User

from nti.dataserver.users.common import set_user_creation_site
from nti.dataserver.users.common import user_creation_sitename
from nti.dataserver.users.common import remove_user_creation_site

from nti.dataserver.users.utils import get_users_by_site
from nti.dataserver.users.utils import is_email_verified
from nti.dataserver.users.utils import get_community_members
from nti.dataserver.users.utils import force_email_verification
from nti.dataserver.users.utils import unindex_email_verification


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
        
    @WithMockDSTrans
    def test_get_user_by_site(self):
        user = User.create_user(username=u'ichigo@bleach.org',
                                external_value={'email': u"ichigo@bleach.org"})
        remove_user_creation_site(user)
        set_user_creation_site(user, u'bleach.org')
        assert_that(user_creation_sitename(user), is_('bleach.org'))
        lifecycleevent.modified(user)
        
        results = get_users_by_site('bleach.org')
        assert_that(results, has_length(1))
        
    @WithMockDSTrans
    def test_get_community_members(self):
        ichigo = User.create_user(username=u'ichigo@bleach.org',
                                  external_value={'email': u"ichigo@bleach.org",
                                                  'email_verified': True})

        rukia = User.create_user(username=u'rukia@bleach.org',
                                 external_value={'email': u"rukia@bleach.org",
                                                 'email_verified': True})
        community = Community.create_entity(username=u'bleach')

        ichigo.record_dynamic_membership(community)
        rukia.record_dynamic_membership(community)

        members = list(get_community_members(community))
        assert_that(members, has_length(2))
