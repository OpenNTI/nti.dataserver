#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os

from zope import component

from nti.contentlibrary import interfaces as lib_interfaces
from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary

from nti.dataserver.users import User

from nti.store import _content_roles as content_roles

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, has_length)

class TestContentRoles(ConfiguringTestBase):

	def setUp(self):
		library = FileLibrary(os.path.join(os.path.dirname(__file__), 'library'))
		component.provideUtility(library, lib_interfaces.IFilesystemContentPackageLibrary)

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
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

		roles = content_roles._get_users_content_roles(user)
		assert_that(roles, is_([(u'mn', u'miladycosmetology.cosmetology')]))

	@WithMockDSTrans
	def test_remove_users_content_roles(self):
		user = self._create_user()
		items = (u"tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.learning_objectives",)
		roles_added = content_roles._add_users_content_roles(user, items)
		assert_that(roles_added, is_(1))

		roles_removed = content_roles._remove_users_content_roles(user, items)
		assert_that(roles_removed, is_(1))

	def test_get_descendants(self):
		library = component.queryUtility(lib_interfaces.IContentPackageLibrary)
		ntiid = u"tag:nextthought.com,2011-10:MN-HTML-MiladyCosmetology.learning_objectives"
		unit = content_roles._get_collection_root(library, ntiid)
		d = list(content_roles._get_descendants(unit))
		assert_that(d, has_length(3))


