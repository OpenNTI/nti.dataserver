import unittest

import nti.dataserver
from nti.dataserver import users 
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.utils import nti_create_friendslist as nti_cfl

from ..ghost_containers import _check_users

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.tests import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_)

class TestGhostContainers(ConfiguringTestBase):
	
	set_up_packages = (nti.dataserver,)
	
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = users.User.create_user( ds, username=username, password=password)
		return usr
		
	@WithMockDSTrans
	def test_containers(self):
		self._create_user()
		_check_users(usernames=('nt@nti.com',))
			
if __name__ == '__main__':
	unittest.main()
	
		
