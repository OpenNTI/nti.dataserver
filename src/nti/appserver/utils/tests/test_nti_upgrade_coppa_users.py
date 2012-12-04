import unittest

from zope import interface
from zope import component

import nti.appserver 
from nti.appserver import site_policies
from nti.appserver.utils import nti_upgrade_coppa_users as nucu

import nti.dataserver
from nti.dataserver import users 
from nti.dataserver import interfaces as nti_interfaces

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.tests import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_)

class TestNTIUpgradeCoppaUsers(ConfiguringTestBase):
	
	set_up_packages = (nti.dataserver, nti.appserver)
	
	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		user = users.User.create_user(ds, username=username, password=password)
		interface.alsoProvides( user, site_policies.IMathcountsCoppaUserWithoutAgreement)
		return user
		
	@WithMockDSTrans
	def test_upgrade_user(self):
		self._create_user()
		site_name = "mathcounts.nextthought.com"
		site_policy = component.queryUtility(site_policies.ISitePolicyUserEventListener, name=site_name)
		users = nucu._process_users(('nt@nti.com',), site_policy)
		assert_that(users, has_length(1))
		user = users[0]
		assert_that(nti_interfaces.ICoppaUserWithAgreement.providedBy(user), is_(True))
		assert_that(nti_interfaces.ICoppaUserWithAgreementUpgraded.providedBy(user), is_(True))
		assert_that(site_policies.IMathcountsCoppaUserWithAgreementUpgraded.providedBy(user), is_(True))
		
if __name__ == '__main__':
	unittest.main()
	
		
