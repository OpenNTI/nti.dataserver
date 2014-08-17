#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#pylint: disable=R0904,W0212

import unittest

from nti.testing.matchers import verifiably_provides
from hamcrest import assert_that
from hamcrest import is_, is_not
from hamcrest import has_property
from hamcrest import greater_than
from hamcrest import has_item

from nti.socketio.dataserver_session import Session
from ..persistent_session import AbstractSession as PersistentSession
from nti.socketio import interfaces as sio_interfaces

class TestSession(unittest.TestCase):

	def test_session_provides(self):
		assert_that( Session(), verifiably_provides( sio_interfaces.ISocketSession ) )

		assert_that( str(Session()), is_( str ) )
		assert_that( repr(Session()), is_( str ) )

	def test_heartbeat_time(self):
		session = PersistentSession()
		assert_that( session, has_property( 'last_heartbeat_time', 0 ) )
		session.heartbeat()
		assert_that( session, has_property( 'last_heartbeat_time', greater_than( 0 ) ) )


	def test_equality(self):

		session1 = Session()
		session2 = Session()

		assert_that( session1, is_( session2 ) )
		assert_that( set((session1,)), has_item( session2 ) )

		session1.session_id = 'a'
		assert_that( session1, is_not( session2 ) )

		assert_that( set((session1,)), is_not( has_item( session2 ) ) )

	def test_resolve(self):

		session1 = Session()
		session2 = Session()

		session3 = Session()

		session3._p_resolveConflict( session1.__getstate__(),
									 session2.__getstate__(), session3.__getstate__() )

		session2._broadcast_connect = True
		session2.state = sio_interfaces.SESSION_STATE_DISCONNECTING
		session3.state = sio_interfaces.SESSION_STATE_DISCONNECTED

		resolved_state = session3._p_resolveConflict( session1.__getstate__(),
													  session2.__getstate__(),
													  session3.__getstate__() )

		session3.__setstate__( resolved_state )
		assert_that( session3, has_property( 'state', sio_interfaces.SESSION_STATE_DISCONNECTED ) )
		assert_that( session3, has_property( '_broadcast_connect', True ) )
