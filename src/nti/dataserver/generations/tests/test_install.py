#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import is_, is_not, none
from hamcrest import has_property
from hamcrest import contains
from nti.tests import verifiably_provides

from zope.component.hooks import site
from zope.component import eventtesting

from zope import component
from zc import intid as zcid_interfaces

from zope.catalog.interfaces import ICatalog
from zope.container import contained
import persistent

from nti.dataserver.utils.example_database_initializer import ExampleDatabaseInitializer
from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import mock_db_trans

import fudge

class PersistentContained(contained.Contained,persistent.Persistent):
	pass

class TestInstall(mock_dataserver.ConfiguringTestBase):

	@mock_dataserver.WithMockDSTrans
	def test_install_creates_intid_utility_and_contained_objects_are_registered(self):
		eventtesting.setUp(self)
		intids = component.getUtility( zcid_interfaces.IIntIds )
		assert_that( intids, verifiably_provides( zcid_interfaces.IIntIds ) )

		ds = self.ds

		contained_obj = PersistentContained()
		ds.root['NewKey'] = contained_obj

		assert_that( contained_obj, has_property( '__parent__', ds.root ) )
		assert_that( contained_obj, has_property( '__name__', 'NewKey' ) )

		assert_that( intids.getId( contained_obj ), is_not( none() ) )
		assert_that( intids.getObject( intids.getId( contained_obj ) ), is_( contained_obj ) )

		del ds.root['NewKey']
		assert_that( intids.queryId( contained_obj ), is_( none() ) )

	@mock_dataserver.WithMockDS
	def test_installed_catalog(self):
		with mock_db_trans( ) as conn:

			context = fudge.Fake().has_attr( connection=conn )

			ExampleDatabaseInitializer(max_test_users=0,skip_passwords=True).install( context )


		with mock_db_trans( ) as conn:
			ds_folder = context.connection.root()['nti.dataserver']

			with site(ds_folder):
				ent_catalog = component.getUtility(ICatalog, name='nti.dataserver.++etc++entity-catalog')
				results = list(ent_catalog.searchResults( email=('Jason.madden@nextthought.com','jason.madden@nextthought.com') ))
				assert_that( results, contains( ds_folder['users']['jason.madden@nextthought.com'] ) )

				results = list(ent_catalog.searchResults( realname=('JASON MADDEN','JASON MADDEN') ))
				assert_that( results, contains( ds_folder['users']['jason.madden@nextthought.com'] ) )
