import unittest

import nti.dataserver
from nti.dataserver import users 
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.utils import nti_add_remove_friends as nti_arf

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.testing.base import ConfiguringTestBase

from hamcrest import (assert_that,  has_item, has_length)

class MockArgs(object):
	def __init__(self):
		self.owner = None
		self.name = None
		self.verbose= False
		self.add_members = ()
		self.remove_members =  ()

class TestAddRemoveFriends(ConfiguringTestBase):
	
	set_up_packages = (nti.dataserver,)
	
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = users.User.create_user( ds, username=username, password=password)
		return usr
		
	def create_fl(self, owner, username='fl@nti.com', name='myfriends', members=()):
		fl = users.FriendsList(username=username)
		fl.creator = owner
		user_interfaces.IFriendlyNamed( fl ).realname = unicode(name)
		for member in members or ():
			fl.addFriend( member )
		owner.addContainedObject(fl)	
		return fl

	@WithMockDSTrans
	def test_simple_add(self):
		owner = self._create_user()
		friend = self._create_user('friend@nti.com')
		friend2 = self._create_user('friend2@nti.com')
		fl = self.create_fl(owner, members=(friend,) )
		current_friends = {x for x in fl}
		assert_that(current_friends, has_length(1))
		fl = nti_arf.add_remove_friends(owner, 'myfriends', ('friend2@nti.com',))
		current_friends = {x for x in fl}
		assert_that(current_friends, has_item(friend))
		assert_that(current_friends, has_item(friend2))
		
	@WithMockDSTrans
	def test_simple_remove(self):
		owner = self._create_user()
		friend = self._create_user('friend@nti.com')
		friend2 = self._create_user('friend2@nti.com')
		fl = self.create_fl(owner, members=(friend,friend2) )
		current_friends = {x for x in fl}
		assert_that(current_friends, has_length(2))
		fl = nti_arf.add_remove_friends(owner, 'myfriends', remove_members=('friend@nti.com',))
		current_friends = {x for x in fl}
		assert_that(current_friends, has_item(friend2))
		assert_that(current_friends, not has_item(friend))
		
	@WithMockDSTrans
	def test_args(self):
		owner = self._create_user()
		friend = self._create_user('friend@nti.com')
		friend2 = self._create_user('friend2@nti.com')
		self.create_fl(owner)
		args = MockArgs()
		args.owner= 'nt@nti.com'
		args.name = 'fl@nti.com'
		args.add_members =  ('friend@nti.com', 'friend2@nti.com')
		fl = nti_arf.process_params(args)
		current_friends = {x for x in fl}
		assert_that(current_friends, has_item(friend2))
		assert_that(current_friends, has_item(friend))
		
if __name__ == '__main__':
	unittest.main()
	
		
