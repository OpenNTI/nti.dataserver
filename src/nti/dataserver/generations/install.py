#!/usr/bin/env python
"""zope.generations installer for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 16

from zope.generations.generations import SchemaManager

class _DataserverSchemaManager(SchemaManager):
	"A schema manager that we can register as a utility in ZCML."
	def __init__( self ):
		super( _DataserverSchemaManager, self ).__init__(generation=generation,
														 minimum_generation=generation,
														 package_name='nti.dataserver.generations')


def evolve( context ):
	install_main( context )
	install_chat( context )

import BTrees
from BTrees import OOBTree
from persistent.list import PersistentList

from zope import interface
from zope.component.interfaces import ISite
from zope.site import LocalSiteManager
from zope.site.folder import Folder, rootFolder
from zope.location.location import locate

import zope.intid
import zc.intid.utility

from nti.chatserver.chatserver import PersistentMappingMeetingStorage
from nti.dataserver import datastructures, _Dataserver
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import sessions
from nti.dataserver import containers as container

import copy
def install_chat( context ):

	conn = context.connection
	room_name = 'meeting_rooms'
	sess_conn = conn.get_connection( 'Sessions' )
	sess_root = sess_conn.root()

	if room_name not in sess_root:
		sess_root[room_name] = PersistentMappingMeetingStorage( OOBTree.OOBTree )

def install_main( context ):
	conn = context.connection
	root = conn.root()

	# The root folder
	root_folder = rootFolder()
	# The root is generally presumed to be an ISite, so make it so
	root_sm = LocalSiteManager( None, default_folder=False ) # No parent site, so parent == global
	conn.add( root_sm ) # Ensure we have a connection so we can become KeyRefs
	conn.add( root_folder ) # Ensure we have a connection so we can become KeyRefs
	root_folder.setSiteManager( root_sm )
	assert ISite.providedBy( root_folder )

	dataserver_folder = Folder()
	interface.alsoProvides( dataserver_folder, nti_interfaces.IDataserverFolder )
	#locate( dataserver_folder, root_folder, name='dataserver2' )
	root_folder['dataserver2'] = dataserver_folder
	assert dataserver_folder.__parent__ is root_folder
	assert dataserver_folder.__name__ == 'dataserver2'

	lsm = LocalSiteManager( root_sm )
	# Change the dataserver_folder from IPossibleSite to ISite
	dataserver_folder.setSiteManager( lsm )
	assert ISite.providedBy( dataserver_folder )

	# FIXME: These should almost certainly be IFolder implementations?
	# TODO: the 'users' key should probably be several different keys, one for each type of
	# Entity object; that way traversal works out much nicer and dataserver_pyramid_views is
	# simplified through dropping UserRootResource in favor of normal traversal
	for key in ('users', 'vendors', 'library', 'quizzes', 'providers' ):
		dataserver_folder[key] = container.CaseInsensitiveLastModifiedBTreeContainer()
		dataserver_folder[key].__name__ = key

	if 'Everyone' not in dataserver_folder['users']:
		# Hmm. In the case that we're running multiple DS instances in the
		# same VM, our constant could wind up with different _p_jar
		# and _p_oid settings. Hence the copy
		dataserver_folder['users']['Everyone'] = copy.deepcopy( users.EVERYONE_PROTO )
	# This is interesting. Must do this to ensure that users
	# that get created at different times and that have weak refs
	# to the right thing. What's a better way?
	# TODO: Probably the better way is through references. See
	# gocept.reference
	users.EVERYONE = dataserver_folder['users']['Everyone']

	# By keeping track of changes in one specific place, and weak-referencing
	# them elsewhere, we can control how much history is kept in one place.
	# This also solves the problem of 'who owns the change?' We do.
	# TODO: This can probably go away now?
	dataserver_folder['changes'] = PersistentList()

	# Install the site manager and register components
	root['nti.dataserver_root'] = root_folder
	root['nti.dataserver'] = dataserver_folder

	oid_resolver =  _Dataserver.PersistentOidResolver()
	conn.add( oid_resolver )
	lsm.registerUtility( oid_resolver, provided=nti_interfaces.IOIDResolver )

	sess_conn = conn.get_connection( 'Sessions' )
	storage = sessions.SessionServiceStorage()
	sess_conn.add( storage )
	sess_conn.root()['session_storage'] = storage
	lsm.registerUtility( storage, provided=nti_interfaces.ISessionServiceStorage )

	# A utility to create intids for any object that needs it
	# Two choices: With either one of them registered, subscribers
	# fire forcing objects to be adaptable to IKeyReference.
	# Int ids are not currently being used, but plans are for the
	# near future. A migration path will have to be established.
	#intids = zope.intid.IntIds( family=BTrees.family64 )
	intids = zc.intid.utility.IntIds('_ds_intid', family=BTrees.family64 )
	lsm.registerUtility( intids, provided=zope.intid.IIntIds )
