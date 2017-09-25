#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import unittest

from nti.chatserver.interfaces import IMeeting

from nti.chatserver.meeting import _Meeting as Meeting


class TestMeeting(unittest.TestCase):

    def test_interface(self):
        assert_that(Meeting(), verifiably_provides(IMeeting))
        meeting = Meeting()
        meeting.creator = u'foo'
        meeting.RoomId = u'1'
        assert_that(meeting, validly_provides(IMeeting))
