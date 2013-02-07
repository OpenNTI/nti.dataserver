#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import unittest

from zope import component

from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary

from nti.dataserver.users import User

from nti.store import _content_roles as content_roles

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_)

class TestContentRoles(ConfiguringTestBase):

	def setUp( self ):
		library = FileLibrary( os.path.join( os.path.dirname(__file__), 'library' ) )
		component.provideUtility( library )

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user( self.ds, username=username, password=password)
		return usr
		
	@WithMockDSTrans
	def test_add_users_content_roles(self):		
		user = self._create_user()
		items = (u"tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.learning_objectives",)
		roles_added = content_roles._add_users_content_roles(user, items)
		assert_that(roles_added, is_(1))
		
		items = (u"tag:nextthought.com,2011-10:MN-HTML-NoCosmetology.learning_objectives",)
		roles_added = content_roles._add_users_content_roles(user, items)
		assert_that(roles_added, is_(0))
		
		
if __name__ == '__main__':
	unittest.main()
	
