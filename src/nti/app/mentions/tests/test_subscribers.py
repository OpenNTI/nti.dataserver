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

from zope import component
from zope import interface

from zope.component import eventtesting
from zope.event import notify

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.layers import AppLayerTest

from nti.dataserver.contenttypes import Note

from nti.dataserver.interfaces import IMentionsUpdateInfo
from nti.dataserver.interfaces import IStreamChangeEvent
from nti.dataserver.interfaces import StreamChangeAcceptedByUser

from nti.dataserver.mentions.interfaces import IPreviousMentions

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import User

from nti.schema.interfaces import IBeforeSequenceAssignedEvent

from nti.contentfragments.interfaces import IPlainTextContentFragment


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


@interface.implementer(IPreviousMentions)
class MockPreviousMentions(object):

    def __init__(self):
        self.notified_mentions = set()

    def add_notification(self, user):
        self.users.add(user)


@interface.implementer(IStreamChangeEvent)
class MockChange(object):
    type = "Created"

    def __init__(self, obj):
        self.object = obj
        self.previous_mentions = \
            IPreviousMentions(obj, None) or MockPreviousMentions()

    def __conform__(self, iface):
        if IPreviousMentions.isOrExtends(iface):
            return self.previous_mentions


class TestUserMentionNotification(ApplicationLayerTest):

    @WithSharedApplicationMockDS
    def test(self):
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(self.ds, username=u'bobby.hagen@nextthought.com')
            snickers = User.create_user(self.ds, username=u'snickers@nextthought.com')
            twix = User.create_user(self.ds, username=u'twix@nextthought.com')

            # With no mentionable, nothing happens
            # i.e. add_notification shouldn't be called on prev_mentions
            change = MockChange(object())
            notify(StreamChangeAcceptedByUser(change, user))
            assert_that(change.previous_mentions.notified_mentions,
                        has_length(0))

            # User not mentioned, nothing happens
            change = MockChange(Note())
            notify(StreamChangeAcceptedByUser(change, user))
            assert_that(change.previous_mentions.notified_mentions,
                        has_length(0))

            # User newly mentioned, so added
            note = Note()
            note.creator = snickers
            note.addSharingTarget(user)
            note.mentions = (IPlainTextContentFragment(user.username),)
            mentions_info = component.getMultiAdapter((note, set()), IMentionsUpdateInfo)
            change = MockChange(note)
            change.mentions_info = mentions_info
            notify(StreamChangeAcceptedByUser(change, user))
            assert_that(change.previous_mentions.notified_mentions,
                        has_length(1))
