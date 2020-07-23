#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six
import time

import fudge
from ZODB.interfaces import IConnection
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import empty
from hamcrest import has_property
from hamcrest import is_
from nti.contentfragments.interfaces import IUnicodeContentFragment
from nti.contentrange import contentrange

from nti.coremetadata.interfaces import ISharingTargetEntityIterable
from nti.dataserver.contenttypes import Note
from nti.dataserver.interfaces import IEntity
from nti.dataserver.interfaces import IMentionsUpdateInfo
from nti.dataserver.mentions.interfaces import IPreviousMentions
from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.users import Community
from nti.externalization.proxy import removeAllProxies
from zope import component

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.layers import AppLayerTest
from nti.contentfragments.interfaces import PlainTextContentFragment

from nti.contentfragments.interfaces import IPlainTextContentFragment


_unset = object()


class TestValidMentionableEntityIterable(AppLayerTest):

    def test_no_mentions(self):
        notable = Note()
        assert_that(set(ISharingTargetEntityIterable(notable)), empty())

    @WithMockDSTrans
    def test_no_valid_mentions(self):
        pluto = self._create_user(u"pluto")
        self._create_user(u"mickey")

        notable = Note()
        notable.creator = pluto
        notable.mentions = Note.mentions.fromObject([u"pluto", u"mickey"])
        assert_that(set(ISharingTargetEntityIterable(notable)), empty())

    @WithMockDSTrans
    def test_no_creator(self):
        pluto = self._create_user(u"pluto")

        notable = Note()
        notable.creator = pluto
        notable.mentions = Note.mentions.fromObject([u"pluto"])
        assert_that(set(ISharingTargetEntityIterable(notable)), empty())

    @WithMockDSTrans
    @fudge.patch("nti.app.mentions.adapters.make_sharing_security_check_for_object",
                 "nti.app.mentions.adapters.User")
    def test_valid_mentions(self, make_sec_check, user_class):
        def security_check(user):
            return user.username in (u"pluto", u"donald")

        make_sec_check.is_callable().returns(security_check)

        users = {name: self._create_user(name) for name in (u"goofy",
                                                            u"pluto",
                                                            u"mickey",
                                                            u"donald")}
        user_class.provides("get_user").calls(lambda name: users.get(name))

        notable = Note()
        notable.mentions = Note.mentions.fromObject([u"goofy", u"pluto", u"mickey", u"donald"])
        assert_that(ISharingTargetEntityIterable(notable),
                    contains(has_property(u"username", u"pluto"),
                             has_property(u"username", u"donald")))


class TestMentionAttributesProvider(AppLayerTest):

    def test_additional_allowed_attrs(self):
        attrs_to_test = ["data-nti-entity-contiguous",
                         "data-nti-entity-has-preview",
                         "data-nti-entity-href",
                         "data-nti-entity-id",
                         "data-nti-entity-link-preview",
                         "data-nti-entity-link-type",
                         "data-nti-entity-mutability",
                         "data-nti-entity-type",
                         "data-nti-entity-username"]

        for attr in attrs_to_test:
            html = '<html><body><a %s="my_value">Opie Cunningham</a></body></html>' % attr
            assert_that(IUnicodeContentFragment(html), is_(html))

        html = '<html><body><a invalid_attr="my_value">Opie Cunningham</a></body></html>'
        exp = '<html><body><a>Opie Cunningham</a></body></html>'
        assert_that(IUnicodeContentFragment(html), is_(exp))


class TestMentionsUpdateInfo(AppLayerTest):

    CONTAINER_ID = 'tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.the_twentieth_century'

    def _setup_users(self):
        self.users = dict()
        tom = self.users['tom'] = self._create_user('tom.findlay')
        andy = self.users['andy'] = self._create_user('andy.cato')
        comm = self.users['comm'] = Community.create_community(self.ds, username=u"groove_comm")
        andy.record_dynamic_membership(comm)
        tom.record_dynamic_membership(comm)
        return comm, tom, andy

    @staticmethod
    def _as_plaintext_tuple(mentions):
        if not mentions:
            return ()

        mentions = [PlainTextContentFragment(mention) for mention in mentions]

        return tuple(mentions)

    def _set_mentions(self, mentionable, mentions):
        if mentions:
            if isinstance(mentions, six.string_types):
                mentions = [mentions]

            mentionable.mentions = self._as_plaintext_tuple(mentions)

    def _set_notified(self, prev_mentions, mentions):
        if mentions:
            if isinstance(mentions, six.string_types):
                mentions = [mentions]

            prev_mentions.notified_mentions = self._as_plaintext_tuple(mentions)

    @staticmethod
    def _set_sharing_targets(mentionable, sharing_targets):
        if sharing_targets:
            if IEntity.providedBy(sharing_targets):
                sharing_targets = [sharing_targets]

            for share in sharing_targets:
                mentionable.addSharingTarget(share)

    def _note(self, creator, mentions=None, sharing_targets=None):
        mentionable = Note()
        mentionable.applicableRange = contentrange.ContentRangeDescription()
        mentionable.containerId = self.CONTAINER_ID
        mentionable.body = (u"Simple body content", )
        mentionable.title = IPlainTextContentFragment(u"Test Title")
        mentionable.createdTime = time.time()
        mentionable.creator = creator

        self._set_mentions(mentionable, mentions)
        self._set_sharing_targets(mentionable, sharing_targets)

        return mentionable

    def _get_mentions_info(self,
                           mentionable,
                           old_shares=None,
                           prev_mentions=None,
                           notified_mentions=None):
        if IEntity.providedBy(old_shares):
            old_shares = [old_shares]

        old_shares = set(old_shares or ())

        if prev_mentions is not None:
            self._set_mentions(IPreviousMentions(mentionable), prev_mentions)
            if prev_mentions == mentionable.mentions:
                IConnection(mentionable).add(IPreviousMentions(mentionable))

        if notified_mentions:
            self._set_notified(IPreviousMentions(mentionable), notified_mentions)

        mentions_info = component.getMultiAdapter((mentionable, old_shares),
                                                  IMentionsUpdateInfo)
        return mentions_info

    def _check_mentions(self, mentions_info, added, shared_to):
        assert_that(mentions_info.mentions_added, is_(added))
        assert_that(mentions_info.mentions_shared_to, is_(shared_to))
        assert_that(mentions_info.new_effective_mentions, is_(added | shared_to))

    def _test_mentions_info(self,
                            old_shares, new_shares,
                            old_mentions, new_mentions,
                            notified_mentions=None):
        comm, tom, andy = [self.users[name] for name in ("comm", "tom", "andy")]

        mentionable = self._note(tom,
                                 sharing_targets=new_shares,
                                 mentions=new_mentions)
        tom.addContainedObject(mentionable)

        mentions_info = self._get_mentions_info(mentionable,
                                                old_shares=old_shares,
                                                prev_mentions=old_mentions)

        # Regardless of change, do not return a user that
        # has already been notified
        notified_mentions = [user.username
                             for user in mentions_info.new_effective_mentions]
        notified_mentions_info = \
            self._get_mentions_info(mentionable,
                                    old_shares=old_shares,
                                    prev_mentions=old_mentions,
                                    notified_mentions=notified_mentions)

        self._check_mentions(notified_mentions_info,
                             added=set(),
                             shared_to=set())

        return mentions_info

    @WithMockDSTrans
    def test_no_access(self):
        comm, _, andy = self._setup_users()

        # No Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=(),
            old_mentions=(), new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # New Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=(),
            old_mentions=(), new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # Same Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=(),
            old_mentions=andy.username, new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # Removed Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=(),
            old_mentions=andy.username, new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

    @WithMockDSTrans
    def test_new_direct_access(self):
        comm, _, andy = self._setup_users()

        # No Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=andy,
            old_mentions=(), new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # New Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=andy,
            old_mentions=(), new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to={andy})

        # Same Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=andy,
            old_mentions=andy.username, new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to={andy})

        # Removed Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=andy,
            old_mentions=andy.username, new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

    @WithMockDSTrans
    def test_existing_direct_access(self):
        comm, _, andy = self._setup_users()

        # No Mentions
        mentions_info = self._test_mentions_info(
            old_shares=andy, new_shares=andy,
            old_mentions=(), new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # New Mentions
        mentions_info = self._test_mentions_info(
            old_shares=andy, new_shares=andy,
            old_mentions=(), new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added={andy},
                             shared_to=set())

        # Same Mentions
        mentions_info = self._test_mentions_info(
            old_shares=andy, new_shares=andy,
            old_mentions=andy.username, new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # Removed Mentions
        mentions_info = self._test_mentions_info(
            old_shares=andy, new_shares=andy,
            old_mentions=andy.username, new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

    @WithMockDSTrans
    def test_removed_direct(self):
        comm, _, andy = self._setup_users()

        # No Mentions
        mentions_info = self._test_mentions_info(
            old_shares=andy, new_shares=(),
            old_mentions=(), new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # New Mentions
        mentions_info = self._test_mentions_info(
            old_shares=andy, new_shares=(),
            old_mentions=(), new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # Same Mentions
        mentions_info = self._test_mentions_info(
            old_shares=andy, new_shares=(),
            old_mentions=andy.username, new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # Removed Mentions
        mentions_info = self._test_mentions_info(
            old_shares=andy, new_shares=(),
            old_mentions=andy.username, new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

    @WithMockDSTrans
    def test_new_indirect_access(self):
        comm, _, andy = self._setup_users()

        # No Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=comm,
            old_mentions=(), new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # New Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=comm,
            old_mentions=(), new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to={andy})

        # Same Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=comm,
            old_mentions=andy.username, new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to={andy})

        # Removed Mentions
        mentions_info = self._test_mentions_info(
            old_shares=(), new_shares=comm,
            old_mentions=andy.username, new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

    @WithMockDSTrans
    def test_existing_indirect_access(self):
        comm, _, andy = self._setup_users()

        # No Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=comm,
            old_mentions=(), new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # New Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=comm,
            old_mentions=(), new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added={andy},
                             shared_to=set())

        # Same Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=comm,
            old_mentions=andy.username, new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # Removed Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=comm,
            old_mentions=andy.username, new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

    @WithMockDSTrans
    def test_removed_indirect(self):
        comm, _, andy = self._setup_users()

        # No Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=(),
            old_mentions=(), new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # New Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=(),
            old_mentions=(), new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # Same Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=(),
            old_mentions=andy.username, new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # Removed Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=(),
            old_mentions=andy.username, new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

    @WithMockDSTrans
    def test_existing_indirect_new_direct_access(self):
        comm, _, andy = self._setup_users()

        # No Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=(comm,andy),
            old_mentions=(), new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())

        # New Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=(comm,andy),
            old_mentions=(), new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to={andy})

        # Same Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=(comm,andy),
            old_mentions=andy.username, new_mentions=andy.username
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to={andy})

        # Removed Mentions
        mentions_info = self._test_mentions_info(
            old_shares=comm, new_shares=(comm,andy),
            old_mentions=andy.username, new_mentions=()
        )

        self._check_mentions(mentions_info,
                             added=set(),
                             shared_to=set())
