#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver.users import User

from nti.salesforce.chatter import Chatter

from . import ConfiguringTestBase

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from hamcrest import (assert_that, is_not, none, has_key)

class TestChatter(ConfiguringTestBase):

	def _create_user(self, username='carlos@nextthought.com', password='Saulo213'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_get_auth_token(self):
		user = self._create_user()
		chatter = Chatter(user)
		token = chatter.get_auth_token()
		assert_that(token, is_not(none()))
		assert_that(token, has_key(u'access_token'))
		assert_that(token, has_key(u'instance_url'))
