import unittest

import nti.dataserver
from nti.dataserver import users 
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.utils import nti_create_friendslist as nti_cfl

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.testing.base import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_)

class TestCreateFriendsLists(ConfiguringTestBase):
	
	set_up_packages = (nti.dataserver,)
	
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = users.User.create_user( ds, username=username, password=password)
		return usr
		
	@WithMockDSTrans
	def test_simple_friendslist(self):
		owner = self._create_user()
		friends = []
		for x in xrange(1, 5):
			username = 'friend%s@nti.com' % x
			friends.append(username)
			self._create_user(username)
			
		fl = nti_cfl.create_friends_list(owner, 'fl@nti.com', 'myfriends', friends, dynamic=False)
		current_friends = {x for x in fl}
		assert_that(current_friends, has_length(4))
		assert_that(nti_interfaces.IDynamicSharingTarget.providedBy(fl), is_(False))
		assert_that(user_interfaces.IFriendlyNamed(fl).realname, is_('myfriends') )
			
	@WithMockDSTrans
	def test_simple_dfl(self):
		owner = self._create_user()
		friends = []
		for x in xrange(1, 10):
			username = 'friend%s@nti.com' % x
			friends.append(username)
			self._create_user(username)
			
		fl = nti_cfl.create_friends_list(owner, 'fl@nti.com', 'dlfriends', friends, dynamic=True)
		current_friends = {x for x in fl}
		assert_that(current_friends, has_length(9))
		assert_that(nti_interfaces.IDynamicSharingTarget.providedBy(fl), is_(True))
		assert_that(user_interfaces.IFriendlyNamed(fl).realname, is_('dlfriends') )
		
if __name__ == '__main__':
	unittest.main()
	
		
