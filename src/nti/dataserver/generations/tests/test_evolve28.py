#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import contains

from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve28 import evolve


import nti.tests
import nti.dataserver

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings
import persistent
import persistent.wref

class TestEvolve28(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve28(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			install( context )
			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']

			pilots = jason.getFriendsList( 'Pilots' )
			delattr( pilots, '_friends_wref_set' )
			friends = []
			setattr( pilots, '_friends', friends )
			# A mix of resolved and unresolved
			friends.append( 'luke.skywalker@nextthought.com' )
			friends.append(persistent.wref.WeakRef( pilots.get_entity( 'amelia.earhart@nextthought.com' ) ) )

		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )


		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden@nextthought.com']
			pilots = jason.getFriendsList( 'Pilots' )

			assert_that( sorted(list(pilots)), contains( pilots.get_entity( 'amelia.earhart@nextthought.com' ),
														 pilots.get_entity( 'luke.skywalker@nextthought.com' ) ) )
