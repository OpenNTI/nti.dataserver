#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import fudge

from zope import interface

from nti.dataserver.users import User

from nti.dataserver.generations.evolve54 import evolve

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

from nti.common.deprecated import hides_warnings

class TestEvolve54(mock_dataserver.DataserverLayerTest):

	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr
	
	@hides_warnings
	@WithMockDS
	def test_evolve54(self):
		
		from nti.app.sites.symmys.interfaces import ISymmysUser
		from nti.app.sites.symmys.interfaces import ILinkedInUser
		from nti.app.sites.symmys.interfaces import ISymmysPerson
		
		with mock_db_trans() as conn:
			
			ds = mock_dataserver.current_mock_ds
			user_1 = User.create_user(ds, username='nti-1.com', password='temp001')
			interface.alsoProvides(user_1, ISymmysUser)
			
			user_2 = User.create_user(ds, username='nti-2.com', password='temp001')
			interface.alsoProvides(user_2, ILinkedInUser)
			
			User.create_user(ds, username='nti-3.com', password='temp001')
			
			context = fudge.Fake().has_attr( connection=conn )
			evolve(context)

			user_1 = User.get_user('nti-1.com')
			assert_that(ISymmysPerson.providedBy(user_1), is_(True))
			assert_that(ISymmysUser.providedBy(user_1), is_(False))
			assert_that(ILinkedInUser.providedBy(user_1), is_(False))
			
			user_2 = User.get_user('nti-2.com')
			assert_that(ISymmysPerson.providedBy(user_2), is_(True))
			assert_that(ISymmysUser.providedBy(user_2), is_(False))
			assert_that(ILinkedInUser.providedBy(user_2), is_(False))

			user_3 = User.get_user('nti-3.com')
			assert_that(ISymmysPerson.providedBy(user_3), is_(False))
			assert_that(ISymmysUser.providedBy(user_3), is_(False))
			assert_that(ILinkedInUser.providedBy(user_3), is_(False))
