#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import contains
from hamcrest import has_length
from hamcrest import assert_that

from nti.testing.matchers import is_true
from nti.testing.matchers import is_false
from nti.testing.matchers import validly_provides as verifiably_provides

from nti.testing.time import time_monotonically_increases

import time

from zope import component

from zope.intid import interfaces as intid_interfaces

from zope.component import eventtesting

from nti.contentrange.contentrange import ContentRangeDescription

from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver import flagging

from nti.dataserver.contenttypes import Note as _Note

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest, WithMockDSTrans


def Note():
    n = _Note()
    n.applicableRange = ContentRangeDescription()
    return n


class NonFlaggable(object):
    pass


class TestFlagging(DataserverLayerTest):

    @WithMockDSTrans
    @time_monotonically_increases
    def test_note_flagging(self):
        #"Notes can be flagged and unflagged"
        n = Note()
        component.getUtility(intid_interfaces.IIntIds).register(n)

        assert_that(component.getAdapter(n, nti_interfaces.IGlobalFlagStorage),
                    verifiably_provides(nti_interfaces.IGlobalFlagStorage))
        eventtesting.clearEvents()

        # first time does something
        n.lastModified = 0
        now = time.time()
        assert_that(flagging.flag_object(n, 'foo@bar'), is_true())
        # second time no-op
        assert_that(flagging.flag_object(n, 'foo@bar'), is_(none()))

        # Fired one event
        assert_that(eventtesting.getEvents(nti_interfaces.IObjectFlaggedEvent), 
                    has_length(1))
        # Updated time once
        assert_that(n.lastModified, is_(now + 1))
        n.lastModified = 0

        assert_that(flagging.flags_object(n, 'foo@bar'), is_true())
        assert_that(list(component.getAdapter(n, nti_interfaces.IGlobalFlagStorage).iterflagged()), 
                    contains(n))

        # first time does something
        assert_that(flagging.unflag_object(n, 'foo@bar'), is_true())
        # second time no-op
        assert_that(flagging.unflag_object(n, 'foo@bar'), is_(none()))
        # Fired one event
        assert_that(eventtesting.getEvents(nti_interfaces.IObjectUnflaggedEvent), 
                    has_length(1))
        # updated time once
        assert_that(n.lastModified, is_(now + 2))
        assert_that(flagging.flags_object(n, 'foo@bar'), is_false())

        # If we unregister while flagged, the flagging status changes
        assert_that(flagging.flag_object(n, 'foo@bar'), is_true())
        component.getUtility(intid_interfaces.IIntIds).unregister(n)

        assert_that(flagging.flags_object(n, 'foo@bar'), is_false())

    @WithMockDSTrans
    @time_monotonically_increases
    def test_flagging_non_flaggable(self):
        # arbitrary objects cannot be, but they fail gracefully.
        n = NonFlaggable()
        component.getUtility(intid_interfaces.IIntIds).register(n)

        eventtesting.clearEvents()

        # first time does nothing
        assert_that(flagging.flag_object(n, 'foo@bar'), is_false())

        # Fired no event
        assert_that(eventtesting.getEvents(nti_interfaces.IObjectFlaggedEvent), 
                    has_length(0))

        assert_that(flagging.flags_object(n, 'foo@bar'), is_(none()))

        # first time does nothing
        assert_that(flagging.unflag_object(n, 'foo@bar'), is_false())
        # Fired no event
        assert_that(eventtesting.getEvents(nti_interfaces.IObjectUnflaggedEvent),
                    has_length(0))
