#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_, has_entry, is_not as does_not, has_key
from hamcrest import has_property

from nti.dataserver.generations.install import evolve as install
from nti.dataserver.generations.evolve13 import evolve


import nti.tests
from nti.tests import verifiably_provides

from ZODB import DB, MappingStorage
import fudge

from zope.site.interfaces import IFolder

new_container = "tag:nexthought.com:abc"

class TestEvolve13(nti.tests.ConfiguringTestBase):

	@fudge.patch( 'nti.dataserver.users._get_shared_dataserver' )
	def test_evolve13(self, mock_ds):
		dbs = {}
		db = DB( MappingStorage.MappingStorage(), databases=dbs )
		DB( MappingStorage.MappingStorage(), databases=dbs, database_name='Sessions' )
		context = fudge.Fake().has_attr( connection=db.open() )

		mock_ds.is_callable().returns_fake().is_a_stub()

		install( context )
		_create_class_with_enclosure( context )

		evolve( context )

		provider = context.connection.root()['nti.dataserver']['providers']['OU']
		assert_that( provider.containers, has_property( '__parent__', provider ) )
		assert_that( provider.containers, has_property( '__name__', '' ) )
		# The existing parent for Classes did not change
		assert_that( provider.getContainer( 'Classes' ), has_property( '__parent__', provider ) )
		assert_that( provider.getContainer( 'Classes' ), has_property( '__name__',  'Classes' ) )
		assert_that( provider.getContainer( new_container ), has_property( '__parent__', provider.containers ) )
		assert_that( provider.getContainer( new_container ), has_property( '__name__', new_container ) )

		# And the enclosure name is fixed
		assert_that( context.connection.root()['nti.dataserver']['providers']['OU'].getContainedObject( 'Classes', 'CS5201' ),
					 has_property( '_enclosures', has_property( '__name__', '' ) ) )



from nti.dataserver import providers
from nti.dataserver import enclosures
from nti.dataserver import classes
from nti.dataserver import contenttypes

def _create_class_with_enclosure( context ):
	conn = context.connection
	root = conn.root()

	folder = root['nti.dataserver']

	ou = folder['providers']['OU'] = providers.Provider( 'OU' )
	clazz = classes.ClassInfo( ID='CS5201' )
	clazz.containerId = 'Classes'
	ou.addContainedObject( clazz )

	clazz.add_enclosure( enclosures.SimplePersistentEnclosure( name='foo', data='' ) )


	new_obj = contenttypes.Highlight()
	new_obj.containerId = new_container
	ou.addContainedObject( new_obj )

	# Emulate the bad names from before
	del ou.containers.__parent__
	del ou.containers.__name__

	del ou.containers[new_container].__parent__
	del ou.containers[new_container].__name__
