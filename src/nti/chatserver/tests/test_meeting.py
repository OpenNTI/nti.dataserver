#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry

import unittest
from nti.testing.matchers import verifiably_provides
from nti.testing.matchers import validly_provides

from nti.chatserver.meeting import _Meeting as Meeting
from nti.chatserver import interfaces as chat_interfaces

class TestMeeting(unittest.TestCase):
	def test_interface(self):

		assert_that( Meeting(), verifiably_provides( chat_interfaces.IMeeting ) )

		meeting = Meeting()
		meeting.creator = 'foo'
		meeting.RoomId = '1'

		assert_that( meeting, validly_provides( chat_interfaces.IMeeting ) )
