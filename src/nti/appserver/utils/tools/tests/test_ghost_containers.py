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

import nti.dataserver
from nti.dataserver import users 
from nti.dataserver.contenttypes import Note

from ..ghost_containers import _check_users

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.tests import ConfiguringTestBase

from hamcrest import (assert_that, has_length, has_entry)

class TestGhostContainers(ConfiguringTestBase):
	
	set_up_packages = (nti.dataserver,)
	
	def setUp(self):
		super(TestGhostContainers, self).setUp()
		library = FileLibrary(os.path.join(os.path.dirname(__file__)))
		component.provideUtility(library, lib_interfaces.IFilesystemContentPackageLibrary)

	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = users.User.create_user( ds, username=username, password=password)
		return usr
		
	@WithMockDSTrans
	def test_containers(self):
		user = self._create_user()
		note = Note()
		note.body = [u'bankai']
		note.creator = user
		note.containerId = u'mycontainer'
		note = user.addContainedObject(note)

		result = _check_users(usernames=('nt@nti.com',))
		assert_that(result, has_length(1))
		assert_that(result, has_entry('nt@nti.com', has_length(1)))
		assert_that(result['nt@nti.com'], has_entry('mycontainer', 1))

	
		
