#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

import fudge
from hamcrest import has_entry
from hamcrest import has_key

from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import not_

from nti.app.mentions.decorators import _CanAccessContentDecorator
from nti.app.mentions.decorators import _IsMentionedDecorator

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.contenttypes import Note

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.externalization.externalization import toExternalObject

from nti.testing.matchers import is_empty


class BaseDecoratorTest(ApplicationLayerTest):

    def _decorate(self, decorator, context, auth_userid):
        external = toExternalObject(context, decorate=False)
        decorator = decorator(context, None)
        decorator.authenticated_userid = auth_userid
        decorator.decorateExternalMapping(context, external)
        return external


class TestIsMentioned(BaseDecoratorTest):

    @WithMockDSTrans
    def test_mentioned(self):
        user = self._create_user(u"b.wyatt")
        note = Note()
        note.mentions = Note.mentions.fromObject((user.username,))
        external = self._decorate(_IsMentionedDecorator, note, user.username)
        assert_that(external, has_entry('isMentioned', True))

    @WithMockDSTrans
    def test_mentions_different_user(self):
        user = self._create_user(u"b.wyatt")
        note = Note()
        note.mentions = Note.mentions.fromObject((user.username,))
        external = self._decorate(_IsMentionedDecorator, note, u"l.knope")
        assert_that(external, not_(has_key("isMentioned")))

    @WithMockDSTrans
    def test_not_authenticated(self):
        user = self._create_user(u"b.wyatt")
        note = Note()
        note.mentions = Note.mentions.fromObject((user.username,))
        external = self._decorate(_IsMentionedDecorator, note, None)
        assert_that(external, not_(has_key("isMentioned")))


class TestCanAccessContentDecorator(BaseDecoratorTest):

    @WithMockDSTrans
    def test_not_authenticated(self):
        user = self._create_user(u"b.wyatt")
        note = Note()
        note.mentions = Note.mentions.fromObject((user.username,))
        external = self._decorate(_CanAccessContentDecorator, note, None)
        assert_that(external, not_(has_key("UsersMentioned")))

    @WithMockDSTrans
    def test_no_mentions(self):
        user = self._create_user(u"b.wyatt")
        note = Note()
        external = self._decorate(_CanAccessContentDecorator, note, user.username)
        assert_that(external, not_(has_key("UsersMentioned")))

    @WithMockDSTrans
    @fudge.patch("nti.app.mentions.decorators.User")
    def test_user_not_found(self, user_class):
        user = self._create_user(u"b.wyatt")
        user_class.provides("get_user").returns(None)
        note = Note()
        note.mentions = Note.mentions.fromObject((user.username,))
        external = self._decorate(_CanAccessContentDecorator, note, u"l.knope")
        assert_that(external, has_entry("UsersMentioned", is_empty()))

    @WithMockDSTrans
    @fudge.patch("nti.app.mentions.decorators.make_sharing_security_check_for_object")
    def test_no_access(self, make_sec_check):
        make_sec_check.is_callable().returns_fake().is_callable().returns(False)
        user = self._create_user(u"b.wyatt")
        note = Note()
        note.mentions = Note.mentions.fromObject((user.username,))
        external = self._decorate(_CanAccessContentDecorator, note, u"l.knope")
        assert_that(external, has_entry("UsersMentioned", has_length(1)))
        assert_that(external["UsersMentioned"][0], has_entry("CanAccessContent", is_(False)))

    @WithMockDSTrans
    @fudge.patch("nti.app.mentions.decorators.make_sharing_security_check_for_object")
    def test_can_access(self, make_sec_check):
        make_sec_check.is_callable().returns_fake().is_callable().returns(True)
        user = self._create_user(u"b.wyatt")
        note = Note()
        note.mentions = Note.mentions.fromObject((user.username,))
        external = self._decorate(_CanAccessContentDecorator, note, u"l.knope")
        assert_that(external, has_entry("UsersMentioned", has_length(1)))
        assert_that(external["UsersMentioned"][0], has_entry("CanAccessContent", is_(True)))

