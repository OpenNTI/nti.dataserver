#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_, has_entry, is_not as does_not, has_key
from hamcrest import not_none
from hamcrest import has_property
from hamcrest import same_instance

from nti.dataserver.generations.install import evolve as install
from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.generations.evolve14 import evolve

from nti.dataserver import containers
from nti.dataserver import datastructures
from nti.dataserver import dicts


import nti.tests
import nti.dataserver
import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.tests import verifiably_provides

from ZODB import DB, MappingStorage
from BTrees.OOBTree import OOBTree
import fudge

from nti.deprecated import hides_warnings

from zope.site.interfaces import IFolder

new_container = "tag:nexthought.com:abc"

class TestEvolve14(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@WithMockDSTrans
	@hides_warnings
	def test_evolve14(self):

		context = fudge.Fake().has_attr( connection=nti.dataserver.tests.mock_dataserver.current_transaction )


		install( context )
		ExampleDatabaseInitializer().install( context )

		ds_folder = context.connection.root()['nti.dataserver']
		jason = ds_folder['users']['jason.madden@nextthought.com']

		# Give me some data to migrate over
		jason.containers.containers = datastructures.KeyPreservingCaseInsensitiveModDateTrackingOOBTree( jason.containers.containers )
		assert_that( jason.containers.containers, has_key( 'FriendsLists' ) )
		# Old ones had a 'Last Modified' key and not a _lastModified attribute
		jason_friends_lists = jason.containers.containers['FriendsLists']
		jason_friends_lists._SampleContainer__data['Last Modified'] = 1234
		del jason_friends_lists._lastModified

		jason.streamCache = datastructures.ModDateTrackingOOBTree()
		jason.containers.containerType = datastructures.ModDateTrackingBTreeContainer
		c = jason.containers.containers[new_container] = datastructures.ModDateTrackingBTreeContainer()
		c.__name__ = new_container
		c.__parent__ = jason.containers
		c['AKey'] = contenttypes.Note()

		evolve( context )

		# We've got a lot of things to check.
		ds_folder = context.connection.root()['nti.dataserver']
		# First, the root folders got updated
		for k in  ('users', 'vendors', 'library', 'quizzes', 'providers'):
			v = ds_folder[k]
			assert_that( v, is_( containers.CaseInsensitiveLastModifiedBTreeContainer ) )

		# The provider relationships are all good

		provider = ds_folder['providers']['OU']
		assert_that( provider.containers, has_property( '__parent__', provider ) )
		assert_that( provider.containers, has_property( '__name__', '' ) )
		# The existing parent for Classes did not change
		assert_that( provider.getContainer( 'Classes' ), has_property( '__parent__', provider ) )
		assert_that( provider.getContainer( 'Classes' ), has_property( '__name__',  'Classes' ) )
		assert_that( provider.classes, is_( same_instance( provider.getContainer( 'Classes' ) ) ) )
		assert_that( provider.classes, is_( same_instance( provider.getContainer( 'CLASSES' ) ) ) )
		# The type is a plain btree, not a subclass
		assert_that( type(provider.classes._SampleContainer__data), is_( same_instance( OOBTree ) ) )

		# The types and
		jason = ds_folder['users']['jason.madden@nextthought.com']

		assert_that( jason.streamCache, is_( OOBTree ) )
		assert_that( jason.containers.containerType, is_( same_instance(containers.LastModifiedBTreeContainer ) ) )
		assert_that( type( jason.containers.containers[new_container] ), is_( same_instance(containers.LastModifiedBTreeContainer ) ) )
		assert_that( jason.containers.containers[new_container], has_property( '__parent__', jason.containers ) )
		assert_that( jason.containers.containers[new_container]['AKey'], is_( contenttypes.Note ) )

		assert_that( type( jason.friendsLists._SampleContainer__data), is_( same_instance( OOBTree ) ) )
		assert_that( type( jason.devices._SampleContainer__data), is_( same_instance( OOBTree ) ) )
		assert_that( jason.devices, is_( same_instance( jason.getContainer( 'Devices' ) ) ) )
		assert_that( jason.friendsLists, is_( same_instance( jason.getContainer( 'FriendsLists' ) ) ) )
		assert_that( jason.friendsLists, has_property( 'lastModified', 1234 ) )
		assert_that( jason.friendsLists['Everyone'], is_( not_none() ) )
		assert_that( jason.devices, has_property( '__parent__', jason ) )
		assert_that( jason.friendsLists, has_property( '__parent__', jason ) )


from nti.dataserver import providers
from nti.dataserver import enclosures
from nti.dataserver import classes
from nti.dataserver import contenttypes
