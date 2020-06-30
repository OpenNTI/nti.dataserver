#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from hamcrest import assert_that
from hamcrest import is_

from nti.app.notabledata.notables import MentionableNotableFilter

from nti.dataserver.contenttypes import Note

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import Community
from nti.dataserver.users import User

from nti.contentfragments.interfaces import PlainTextContentFragment


class TestMentionableNotableFilter(DataserverLayerTest):

    @WithMockDSTrans
    def test_not_mentionable(self):
        zipper = User.create_user(self.ds, username='zipper')
        obj = object()
        nfilter = MentionableNotableFilter(obj)
        assert_that(nfilter.is_notable(obj, zipper), is_(False))

    @WithMockDSTrans
    def test_not_mentioned(self):
        zipper = User.create_user(self.ds, username='zipper')
        obj = Note()
        nfilter = MentionableNotableFilter(obj)
        assert_that(nfilter.is_notable(obj, zipper), is_(False))

    @WithMockDSTrans
    def test_not_shared_with_nor_tagged(self):
        zipper = User.create_user(self.ds, username='zipper')
        obj = Note()
        obj.mentions = (PlainTextContentFragment(zipper.username),)
        nfilter = MentionableNotableFilter(obj)
        assert_that(bool(nfilter.is_notable(obj, zipper)), is_(False))

    @WithMockDSTrans
    def test_mentioned_and_shared_with(self):
        zipper = User.create_user(self.ds, username='zipper')
        comm = Community.create_community(self.ds, username='test_comm')
        zipper.record_dynamic_membership(comm)

        obj = Note()
        obj.mentions = (PlainTextContentFragment(zipper.username),)
        obj.addSharingTarget(zipper)
        nfilter = MentionableNotableFilter(obj)

        assert_that(nfilter.is_notable(obj, zipper), is_(True))

    @WithMockDSTrans
    def test_mentioned_and_tagged(self):
        zipper = User.create_user(self.ds, username='zipper')

        obj = Note()
        obj.mentions = (PlainTextContentFragment(zipper.username),)
        obj.tags = (PlainTextContentFragment(zipper.NTIID),)
        nfilter = MentionableNotableFilter(obj)

        assert_that(nfilter.is_notable(obj, zipper), is_(True))

