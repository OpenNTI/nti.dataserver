#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,too-many-function-args

from hamcrest import is_
from hamcrest import none
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains

import unittest

from zope import component
from zope import lifecycleevent

from zope.intid.interfaces import IIntIds

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestLayer

from nti.dataserver.users.communities import Community

from nti.dataserver.users.users import User

from nti.dataserver.users.common import set_user_creation_site
from nti.dataserver.users.common import user_creation_sitename
from nti.dataserver.users.common import remove_user_creation_site

from nti.dataserver.users.utils import get_users_by_site
from nti.dataserver.users.utils import get_users_by_email_in_sites
from nti.dataserver.users.utils import invalid_emails_for_emails
from nti.dataserver.users.utils import invalid_emails_for_users
from nti.dataserver.users.utils import is_email_invalid
from nti.dataserver.users.utils import is_email_valid
from nti.dataserver.users.utils import is_email_verified
from nti.dataserver.users.utils import is_user_email_invalid
from nti.dataserver.users.utils import is_user_email_valid
from nti.dataserver.users.utils import get_community_members
from nti.dataserver.users.utils import force_email_verification
from nti.dataserver.users.utils import unindex_email_verification
from nti.dataserver.users.utils import get_entity_alias_from_index
from nti.dataserver.users.utils import get_entity_mimetype_from_index
from nti.dataserver.users.utils import get_entity_realname_from_index
from nti.dataserver.users.utils import valid_emails_for_emails
from nti.dataserver.users.utils import valid_emails_for_users

from nti.mailer.interfaces import IEmailAddressable


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
    def test_is_email_valid(self):
        User.create_user(username=u'ichigo@bleach.org',
                         external_value={'email': u"ichigo@bleach.org",
                                         'email_verified': True})

        User.create_user(username=u'rukia@bleach.org',
                         external_value={'email': u"rukia@bleach.org",
                                         'email_verified': False})

        User.create_user(username=u'foo@bleach.org',
                         external_value={'email': u"foo@bleach.org"})

        User.create_user(username=u'bar@bleach.org',
                         external_value={'email': u"rukia@bleach.org"})

        assert_that(is_email_valid('ichigo@bleach.org'), is_(True))
        assert_that(is_email_valid('ICHIGO@bleach.ORG'), is_(True))
        assert_that(is_email_valid('rukia@bleach.org'), is_(False))
        assert_that(is_email_valid('foo@bleach.org'), is_(True))
        assert_that(is_email_valid('bar@bleach.org'), is_(False))

    @WithMockDSTrans
    def test_is_email_invalid(self):
        User.create_user(username=u'ichigo@bleach.org',
                         external_value={'email': u"ichigo@bleach.org",
                                         'email_verified': True})

        User.create_user(username=u'rukia@bleach.org',
                         external_value={'email': u"rukia@bleach.org",
                                         'email_verified': False})

        User.create_user(username=u'foo@bleach.org',
                         external_value={'email': u"foo@bleach.org"})

        User.create_user(username=u'bar@bleach.org',
                         external_value={'email': u"rukia@bleach.org"})

        assert_that(is_email_invalid('ichigo@bleach.org'), is_(False))
        assert_that(is_email_invalid('ICHIGO@bleach.ORG'), is_(False))
        assert_that(is_email_invalid('rukia@bleach.org'), is_(True))
        assert_that(is_email_invalid('foo@bleach.org'), is_(False))
        assert_that(is_email_invalid('bar@bleach.org'), is_(True))

    @WithMockDSTrans
    def test_is_user_email_valid(self):
        u1 = User.create_user(username=u'ichigo@bleach.org',
                              external_value={'email': u"ichigo@bleach.org",
                                              'email_verified': True})

        u2 = User.create_user(username=u'rukia@bleach.org',
                              external_value={'email': u"rukia@bleach.org",
                                              'email_verified': False})

        u3 = User.create_user(username=u'foo@bleach.org',
                              external_value={'email': u"foo@bleach.org"})

        u4 = User.create_user(username=u'bar@bleach.org',
                              external_value={'email': u"rukia@bleach.org"})

        assert_that(is_user_email_valid(u1), is_(True))
        assert_that(is_user_email_valid(u2), is_(False))
        assert_that(is_user_email_valid(u3), is_(True))
        assert_that(is_user_email_valid(u4), is_(True))

    @WithMockDSTrans
    def test_is_user_email_invalid(self):
        u1 = User.create_user(username=u'ichigo@bleach.org',
                              external_value={'email': u"ichigo@bleach.org",
                                              'email_verified': True})

        u2 = User.create_user(username=u'rukia@bleach.org',
                              external_value={'email': u"rukia@bleach.org",
                                              'email_verified': False})

        u3 = User.create_user(username=u'foo@bleach.org',
                              external_value={'email': u"foo@bleach.org"})

        u4 = User.create_user(username=u'bar@bleach.org',
                              external_value={'email': u"rukia@bleach.org"})

        assert_that(is_user_email_invalid(u1), is_(False))
        assert_that(is_user_email_invalid(u2), is_(True))
        assert_that(is_user_email_invalid(u3), is_(False))
        assert_that(is_user_email_invalid(u4), is_(False))

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
    def test_get_users_by_email_in_sites(self):
        user = User.create_user(username=u'ichigo@bleach.org',
                                external_value={'email': u"ichigo@bleach.org"})
        remove_user_creation_site(user)
        set_user_creation_site(user, u'bleach.org')
        assert_that(user_creation_sitename(user), is_('bleach.org'))
        lifecycleevent.modified(user)

        results = get_users_by_email_in_sites('ichigo@bleach.org', 'bleach.org')
        assert_that(results, has_length(1))

        results = get_users_by_email_in_sites('ichigo@bleach.org', 'alpha.dev')
        assert_that(results, has_length(0))

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

        members = get_community_members(community)
        assert_that(members, has_length(2))

    @WithMockDSTrans
    def test_get_names(self):
        ichigo = User.create_user(username=u'ichigo@bleach.org',
                                  external_value={'email': u"ichigo@bleach.org",
                                                  'realname': u'Ichigo Kurosaki',
                                                  'alias': u'Ichigo',
                                                  'email_verified': True})
        
        intids = component.getUtility(IIntIds)
        doc_id = intids.getId(ichigo)

        alias = get_entity_alias_from_index(doc_id)
        assert_that(alias, is_('ichigo'))
        
        name = get_entity_realname_from_index(doc_id)
        assert_that(name, is_('ichigo kurosaki'))
        
        name = get_entity_mimetype_from_index(doc_id)
        assert_that(name, is_('application/vnd.nextthought.user'))

        name = get_entity_realname_from_index(0)
        assert_that(name, is_(none()))

    @WithMockDSTrans
    def test_valid_emails_for_emails(self):
        ichigo = User.create_user(username=u'ichigo@bleach.org',
                                  external_value={'email': u"ichigo@bleach.org",
                                                  'email_verified': True})

        rukia = User.create_user(username=u'rukia@bleach.org',
                                 external_value={'email': u"rukia@bleach.org",
                                                 'email_verified': False})

        foo = User.create_user(username=u'foo@bleach.org',
                               external_value={'email': u"foo@bleach.org"})

        user_emails = [IEmailAddressable(user).email for user in [ichigo, rukia, foo]]
        emails = valid_emails_for_emails(user_emails)
        assert_that(emails, has_length(2))
        assert_that(emails, contains(u'ichigo@bleach.org', u'foo@bleach.org'))

    @WithMockDSTrans
    def test_invalid_emails_for_emails(self):
        ichigo = User.create_user(username=u'ichigo@bleach.org',
                                  external_value={'email': u"ichigo@bleach.org",
                                                  'email_verified': True})

        rukia = User.create_user(username=u'rukia@bleach.org',
                                 external_value={'email': u"rukia@bleach.org",
                                                 'email_verified': False})

        foo = User.create_user(username=u'foo@bleach.org',
                               external_value={'email': u"foo@bleach.org"})

        user_emails = [IEmailAddressable(user).email for user in [ichigo, rukia, foo]]
        invalid_emails = invalid_emails_for_emails(user_emails)
        assert_that(invalid_emails, has_length(1))
        assert_that(invalid_emails, contains(u'rukia@bleach.org'))

    @WithMockDSTrans
    def test_valid_emails_for_users(self):
        ichigo = User.create_user(username=u'ichigo@bleach.org',
                                  external_value={'email': u"ichigo@bleach.org",
                                                  'email_verified': True})

        rukia = User.create_user(username=u'rukia@bleach.org',
                                 external_value={'email': u"rukia@bleach.org",
                                                 'email_verified': False})

        foo = User.create_user(username=u'foo@bleach.org',
                               external_value={'email': u"foo@bleach.org"})

        bar = User.create_user(username=u'bar@bleach.org',
                               external_value={'email': u"rukia@bleach.org"})

        emails = valid_emails_for_users([ichigo, rukia, foo, bar])
        assert_that(emails, has_length(3))
        assert_that(emails, contains(u'ichigo@bleach.org', u'foo@bleach.org', u'rukia@bleach.org'))

    @WithMockDSTrans
    def test_invalid_emails_for_users(self):
        ichigo = User.create_user(username=u'ichigo@bleach.org',
                                  external_value={'email': u"ichigo@bleach.org",
                                                  'email_verified': True})

        rukia = User.create_user(username=u'rukia@bleach.org',
                                 external_value={'email': u"rukia@bleach.org",
                                                 'email_verified': False})

        foo = User.create_user(username=u'foo@bleach.org',
                               external_value={'email': u"foo@bleach.org"})

        bar = User.create_user(username=u'bar@bleach.org',
                               external_value={'email': u"rukia@bleach.org"})

        invalid_emails = invalid_emails_for_users([ichigo, rukia, foo, bar])
        assert_that(invalid_emails, has_length(1))
        assert_that(invalid_emails, contains(u'rukia@bleach.org'))
