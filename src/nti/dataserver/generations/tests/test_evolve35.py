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


from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve35 import evolve

from BTrees.OOBTree import OOTreeSet


import nti.testing.base
import nti.dataserver
from nti.dataserver import users

import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import  mock_db_trans, WithMockDS

import fudge

from nti.deprecated import hides_warnings



class TestEvolve35(nti.dataserver.tests.mock_dataserver.DataserverLayerTest):


	@hides_warnings
	@WithMockDS
	def test_evolve35(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )

			#install( context )
			ExampleDatabaseInitializer(max_test_users=5,skip_passwords=True).install( context )

			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden']
			jeff = ds_folder['users']['jeff.muehring']
			# Give me some data to migrate over

			jason._sources_not_accepted = OOTreeSet()
			jason._sources_not_accepted.add( jeff.username )

			jason._following = OOTreeSet()
			del jason._entities_followed
			jason._following.add( jeff.username )

			jason._communities = OOTreeSet()
			jason._dynamic_memberships.clear()
			jason._communities.add( 'Everyone' )
			jason._communities.add( 'foo@bar' )


			dfl = users.DynamicFriendsList('Friends')
			dfl.creator = jason

			jason.addContainedObject( dfl )
			dfl.addFriend( jeff )

			jason.muted_oids = OOTreeSet()
			jason.muted_oids.add( 'foo' )



		with mock_db_trans(  ) as conn:
			context = fudge.Fake().has_attr( connection=conn )
			evolve( context )

		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']
			jason = ds_folder['users']['jason.madden']
			jeff = ds_folder['users']['jeff.muehring']
			everyone = ds_folder['users']['Everyone']

			assert_that( list(jason.entities_followed), is_( [jeff] ) )
			assert_that( list(jason.entities_ignoring_shared_data_from), is_( [jeff] ) )
			assert_that( list( jason.dynamic_memberships ), is_( [everyone] ) )

			assert_that( list( jason._muted_oids ), is_( ['foo'] ) )
