from __future__ import print_function

import unittest

from webtest import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, is_)

class TestApplicationUserExporViews(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_user_info_extract(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user(external_value={u'email':u"nti@nt.com"})
			self._create_user(username='rukia@nt.com', external_value={u'email':u'rukia@nt.com'})
			self._create_user(username='ichigo@nt.com', external_value={u'email':u'ichigo@nt.com'})

		testapp = TestApp( self.app )

		path = '/dataserver2/@@user_info_extract'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'
		
		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

if __name__ == '__main__':
	unittest.main()
	