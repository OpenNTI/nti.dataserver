#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals



from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_property
from hamcrest import contains
from hamcrest import starts_with
from hamcrest import is_not as does_not
from hamcrest import has_length


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve37 import evolve

from BTrees.OOBTree import OOTreeSet


import nti.testing.base
import nti.dataserver
from nti.dataserver import users

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.common.deprecated import hides_warnings
from nti.dataserver.users.tests.test_friends_lists import _dfl_sharing_fixture



class TestEvolve37(nti.dataserver.tests.mock_dataserver.DataserverLayerTest):


	@hides_warnings
	@WithMockDS
	def test_evolve37(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			#install( context )
			ExampleDatabaseInitializer(max_test_users=5,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden']
			jason.friendsLists._SampleContainer__data.clear()
			jason.friendsLists._BTreeContainer__len.set( 0 )

			jason.friendsLists['Everyone'] = users.FriendsList('Everyone')
			jason.friendsLists['Everyone'].creator = None
			assert_that( jason.friendsLists, has_length( 1 ) )

		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden']

			assert_that( jason.friendsLists, has_length( 0 ) )
