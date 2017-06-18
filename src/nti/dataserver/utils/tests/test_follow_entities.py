import unittest

import nti.dataserver
from nti.dataserver.users import User
from nti.dataserver.users import Community
from nti.dataserver.utils import nti_follow_entity as nti_follow

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.testing.base import ConfiguringTestBase

from hamcrest import (assert_that, has_item, has_length)

class TestNTIFollowEntities(ConfiguringTestBase):
	
	set_up_packages = (nti.dataserver,)
			
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user( ds, username=username, password=password)
		return usr
		
	def _create_comm(self, username='comm@nti.com'):
		ds = mock_dataserver.current_mock_ds
		comm = Community.create_community(ds, username=username)
		return comm

	@WithMockDSTrans
	def test_simple_follow(self):
		user = self._create_user()
		follow = []
		for x in range(1, 3):
			name = '%s_comm@nti.com' % x
			follow.append(name)
			self._create_comm(name)
			
		found, not_found, member_of = nti_follow.follow_entities(user, follow)
		assert_that(found, has_length(2))
		assert_that(not_found, has_length(0))
		assert_that(member_of, has_length(2))
		
		s = set(user.usernames_of_dynamic_memberships)
		assert_that(s, has_length(3))
		for n in follow:
			assert_that(s, has_item(n))
		
if __name__ == '__main__':
	unittest.main()
	
		
