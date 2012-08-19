
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import sys

from hamcrest import assert_that, is_, has_entry, is_not, has_key
from hamcrest import not_none
from hamcrest import none
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
from nti.assessment import assessed
import nti.dataserver.tests.mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans, mock_db_trans, WithMockDS
from nti.tests import verifiably_provides

from ZODB import DB, MappingStorage
from BTrees.OOBTree import OOBTree
import fudge

from nti.deprecated import hides_warnings

from zope.site.interfaces import IFolder

new_container = "tag:nexthought.com:abc"

class TestEvolve14(nti.dataserver.tests.mock_dataserver.ConfiguringTestBase):
	set_up_packages = (nti.dataserver,)

	@hides_warnings
	@WithMockDS
	def test_evolve14(self):
		with mock_db_trans( ) as conn:
			context = fudge.Fake().has_attr( connection=conn )


			install( context )
			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )

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

			# If an object that was once callable and has implementedBy called on
			# it becomes uncallable, then it becomes impossible to unpickle.
			# Obviously that can mess migrations up. So this test simulates it.
			# assessed.QAssessedQuestion.__call__ = lambda x: None
			# as_q = assessed.QAssessedQuestion()
			# as_q.containerId = new_container
			# nti.dataserver.interfaces.IModeledContent.implementedBy( as_q )
			# del assessed.QAssessedQuestion.__call__
			#jason.addContainedObject( as_q )
			#as_q_id = as_q.id
			## FIXME: The above is now commented out. As of now, when intid subscribers and
			# sublocations are in play, this starts effecting things much sooner and we have
			# no workaround for it.

		# Reset the databases, ensure nothing is cached
		mock_ds = nti.dataserver.tests.mock_dataserver.current_mock_ds
		mock_db = mock_ds.db
		mock_storages = { k: db.storage for k, db in mock_db.databases.items() if db }
		for db in mock_db.databases.values():
			db.close()
		mock_dbs = {}
		{DB( v, databases=mock_dbs, database_name=k ) for k, v in mock_storages.items()}
		mock_ds.db = mock_dbs['Users']



		with mock_db_trans(  ) as conn:
			del sys.modules['nti.assessment.assessed']

			conn.cacheGC()
			conn.cacheMinimize()
			conn._cache.cache_data.clear()

			context = fudge.Fake().has_attr( connection=conn )


			evolve( context )

		with mock_db_trans( ) as conn:
			conn.cacheGC()
			conn.cacheMinimize()
			conn._cache.cache_data.clear()

			context = fudge.Fake().has_attr( connection=conn )


			# We've got a lot of things to check.
			ds_folder = context.connection.root()['nti.dataserver']
			# First, the root folders got updated
			for k in  ('users', 'vendors', 'library', 'quizzes', 'providers'):
				v = ds_folder.get( k, None )
				if v is None: continue
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
			#assert_that( jason.getContainedObject( new_container, as_q_id ), is_( none() ) ) # dropped, invalid



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
