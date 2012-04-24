#!/usr/bin/env python2.7
# disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that,  is_, none, is_not


from zope import component
from zope import interface

from nti.tests import verifiably_provides
import nti.dataserver.interfaces as nti_interfaces
import nti.dataserver.sessions as sessions

import mock_dataserver



class MockSessionService(sessions.SessionService):

	def _spawn_cluster_listener(self):
		class PubSocket(object):
			def send_multipart( self, o ): pass
		self.pub_socket = PubSocket()
		return None

class TestSessionService(mock_dataserver.ConfiguringTestBase):

	def setUp(self):
		super(TestSessionService,self).setUp()
		self.session_service = MockSessionService()
		self.storage = sessions.SessionServiceStorage()
		component.provideUtility( self.storage, provides=nti_interfaces.ISessionServiceStorage )

	def test_get_set_proxy_session(self):
		self.session_service.set_proxy_session( '1', self )
		assert_that( self.session_service.get_proxy_session( '1' ), is_( self ) )
		self.session_service.set_proxy_session( '1' )
		assert_that( self.session_service.get_proxy_session( '1' ), is_( none() ) )

	def test_create_session_deprecated(self):
		self.storage = sessions.SimpleSessionServiceStorage()
		component.provideUtility( self.storage, provides=nti_interfaces.ISessionServiceStorage )
		session = self.session_service.create_session( watch_session=False )
		assert_that( session, is_not( none() ) )
		assert_that( self.session_service.get_session( session.session_id ), is_( session ) )

	def test_create_session(self):
		session = self.session_service.create_session( watch_session=False )
		assert_that( session, is_not( none() ) )
		assert_that( self.session_service.get_session( session.session_id ), is_( session ) )


def test_session_service_storage():
	assert_that( sessions.SessionServiceStorage(), verifiably_provides( nti_interfaces.ISessionServiceStorage ) )
