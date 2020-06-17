#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import fudge
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import empty
from hamcrest import has_property
from hamcrest import is_
from nti.contentfragments.interfaces import IUnicodeContentFragment

from nti.coremetadata.interfaces import ISharingTargetEntityIterable
from nti.dataserver.contenttypes import Note
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.app.testing.layers import AppLayerTest


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
        attrs_to_test = ["data-nti-entity-type",
                         "data-nti-entity-mutability",
                         "data-nti-entity-id",
                         "data-nti-entity-username"]

        for attr in attrs_to_test:
            html = '<html><body><a %s="my_value">Opie Cunningham</a></body></html>' % attr
            assert_that(IUnicodeContentFragment(html), is_(html))

        html = '<html><body><a invalid_attr="my_value">Opie Cunningham</a></body></html>'
        exp = '<html><body><a>Opie Cunningham</a></body></html>'
        assert_that(IUnicodeContentFragment(html), is_(exp))
