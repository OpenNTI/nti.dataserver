#!/usr/bin/env python

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import contains_string

from zope import component
from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

from .test_application import TestApp



class TestSocketioViews(ApplicationLayerTest):


	@WithSharedApplicationMockDS
	def test_connect_bad_transport(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		class S(object):
			pass
		class SM(object):
			def get_session( self, x, **kwargs ):
				return self
			owner = 'foo@bar'
			socket = S()

		component.getUtility( nti_interfaces.IDataserver ).session_manager = SM()
		testapp = TestApp( self.app )
		res = testapp.get( '/socket.io/1/jsonp-polling/1234', extra_environ=self._make_extra_environ(),
						   status=404)

		assert_that( res.body, contains_string( 'Unknown transport type jsonp-polling' ) )

	@WithSharedApplicationMockDS
	def test_connect_bad_session_id(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		class S(object):
			pass
		class SM(object):
			def get_session( self, x, **kwargs ):
				raise ValueError(x)
			owner = 'foo@bar'
			socket = S()

		component.getUtility( nti_interfaces.IDataserver ).session_manager = SM()
		testapp = TestApp( self.app )
		res = testapp.get( '/socket.io/1/jsonp-polling/1234', extra_environ=self._make_extra_environ(),
						   status=404)

		assert_that( res.body, contains_string( 'No session found or illegal session id' ) )

	@WithSharedApplicationMockDS
	def test_handshake(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		class S(object):
			session_id = u'abce'
		class SM(object):
			def create_session( self, **kwargs ):
				return S()
			owner = 'foo@bar'
			socket = S()

		component.getUtility( nti_interfaces.IDataserver ).session_manager = SM()
		testapp = TestApp( self.app )
		res = testapp.get( '/socket.io/1/', extra_environ=self._make_extra_environ(),
						   status=200)

		for name, val in res.headerlist:
			__traceback_info__ = name, val
			assert_that( name, is_( str ) )
			assert_that( val, is_( str ) )
