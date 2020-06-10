#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import has_length
from hamcrest import raises

from pyramid import httpexceptions as hexc

from zope.component import eventtesting

from nti.app.testing.layers import AppLayerTest

from nti.dataserver.contenttypes import Note

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.schema.interfaces import IBeforeSequenceAssignedEvent


class TestValidateMentionsOnSet(AppLayerTest):

    def setUp(self):
        eventtesting.clearEvents()

    def test_no_mentions(self):
        notable = Note()
        notable.mentions = ()
        assert_that(eventtesting.getEvents(IBeforeSequenceAssignedEvent),
                    has_length(1))

    @WithMockDSTrans
    def test_missing_user(self):
        notable = Note()
        assert_that(calling(setattr).with_args(notable,
                                               "mentions",
                                               Note.mentions.fromObject((u"e.ripley",))),
                    raises(hexc.HTTPUnprocessableEntity))

    @WithMockDSTrans
    def test_valid_user(self):
        self._create_user(u"e.ripley")
        notable = Note()
        notable.mentions = Note.mentions.fromObject((u"e.ripley",))
        assert_that(eventtesting.getEvents(IBeforeSequenceAssignedEvent),
                    has_length(1))
