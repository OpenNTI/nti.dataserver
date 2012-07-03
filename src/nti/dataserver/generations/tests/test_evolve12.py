#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that, is_, has_entry, is_not as does_not, has_key
from hamcrest import has_property

from nti.dataserver.generations.evolve12 import evolve


import nti.tests
import nti.deprecated
from nti.tests import verifiably_provides

from ZODB import DB, MappingStorage
import fudge

from zope.site.interfaces import IFolder

class TestEvolve12(nti.tests.ConfiguringTestBase):

	@nti.deprecated.hides_warnings
	def test_evolve12(self):
		dbs = {}
		db = DB( MappingStorage.MappingStorage(), databases=dbs )
		DB( MappingStorage.MappingStorage(), databases=dbs, database_name='Sessions' )
		context = fudge.Fake().has_attr( connection=db.open() )

		install_main( context )
		_create_class_with_enclosure( context )

		evolve( context )

		assert_that( context.connection.root()['nti.dataserver'], verifiably_provides( ISite ) )
		assert_that( context.connection.root()['nti.dataserver'], verifiably_provides( IFolder ) )
		# has_entry doesn't work with a Folder so do the lookup manually
		assert_that( context.connection.root()['nti.dataserver']['users'], is_( datastructures.KeyPreservingCaseInsensitiveModDateTrackingBTreeContainer ) )


		# And the enclosure name is fixed
		assert_that( context.connection.root()['nti.dataserver']['providers']['OU'].getContainedObject( 'Classes', 'CS5201' ),
					 has_property( '_enclosures', has_property( '__name__', '' ) ) )



from BTrees import OOBTree
from persistent.list import PersistentList

from zope.component.interfaces import ISite
from zope.site import LocalSiteManager, SiteManagerContainer
from zope.site.folder import Folder, rootFolder
from zope.location.location import locate

import zope.intid
import zc.intid.utility
import copy

from nti.chatserver.chatserver import PersistentMappingMeetingStorage
from nti.dataserver import datastructures, _Dataserver
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import sessions


def install_main( context ):
	"""
	The install method from version r8259
	"""
	conn = context.connection
	root = conn.root()

	container = SiteManagerContainer()
	lsm = LocalSiteManager( None, default_folder=None ) # No parent
	container.setSiteManager( lsm )

	with nti.deprecated.hiding_warnings():
		for key in ('users', 'vendors', 'library', 'quizzes', 'providers' ):
			lsm[key] = datastructures.KeyPreservingCaseInsensitiveModDateTrackingBTreeContainer()
			lsm[key].__name__ = key

	if 'Everyone' not in lsm['users']:
		# Hmm. In the case that we're running multiple DS instances in the
		# same VM, our constant could wind up with different _p_jar
		# and _p_oid settings. Hence the copy
		lsm['users']['Everyone'] = copy.deepcopy( users.EVERYONE_PROTO )
	# This is interesting. Must do this to ensure that users
	# that get created at different times and that have weak refs
	# to the right thing. What's a better way?
	users.EVERYONE = lsm['users']['Everyone']

	# By keeping track of changes in one specific place, and weak-referencing
	# them elsewhere, we can control how much history is kept in one place.
	# This also solves the problem of 'who owns the change?' We do.
	if not lsm.has_key( 'changes'):
		lsm['changes'] = PersistentList()

	# Install the site manager and register components
	root['nti.dataserver'] = container

	oid_resolver =  _Dataserver.PersistentOidResolver()
	conn.add( oid_resolver )
	lsm.registerUtility( oid_resolver, provided=nti_interfaces.IOIDResolver )

	sess_conn = conn.get_connection( 'Sessions' )
	storage = sessions.SessionServiceStorage()
	sess_conn.add( storage )
	sess_conn.root()['session_storage'] = storage
	lsm.registerUtility( storage, provided=nti_interfaces.ISessionServiceStorage )

from nti.dataserver import providers
from nti.dataserver import enclosures
from nti.dataserver import classes

def _create_class_with_enclosure( context ):
	conn = context.connection
	root = conn.root()

	folder = root['nti.dataserver'].getSiteManager()

	ou = folder['providers']['OU'] = providers.Provider( 'OU' )
	clazz = classes.ClassInfo( ID='CS5201' )
	clazz.containerId = 'Classes'
	ou.addContainedObject( clazz )

	clazz.add_enclosure( enclosures.SimplePersistentEnclosure( name='foo', data='' ) )

	# Emulate the bad names from before
	clazz._enclosures.__name__ = None
