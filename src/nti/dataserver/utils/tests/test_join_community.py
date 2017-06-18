import unittest

import nti.dataserver
from nti.dataserver.users import User
from nti.dataserver.users import Community
from nti.dataserver.utils import nti_join_community as nti_join

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
	def test_join_follow(self):
		user = self._create_user()
		comms = []
		for x in range(1, 6):
			name = '%s_comm@nti.com' % x
			comms.append(name)
			self._create_comm(name)
			
		not_found = nti_join.join_communities(user, comms, follow=True, exitOnError=False)
		assert_that(not_found, has_length(0))	
		followed = {e.username for e in user.entities_followed}
		membership = set(user.usernames_of_dynamic_memberships)
		assert_that(membership, has_length(6))
		for n in comms:
			assert_that(membership, has_item(n))
			assert_that(followed, has_item(n))
			
if __name__ == '__main__':
	unittest.main()
	
		
