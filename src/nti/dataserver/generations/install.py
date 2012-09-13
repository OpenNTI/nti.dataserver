#!/usr/bin/env python
"""zope.generations installer for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 24

from zope.generations.generations import SchemaManager

class _DataserverSchemaManager(SchemaManager):
	"A schema manager that we can register as a utility in ZCML."
	def __init__( self ):
		super( _DataserverSchemaManager, self ).__init__(generation=generation,
														 minimum_generation=generation,
														 package_name='nti.dataserver.generations')


def evolve( context ):
	result = install_main( context )
	install_chat( context )
	return result

import BTrees

from zope import interface
from zope.component.interfaces import ISite
from zope.site import LocalSiteManager
from zope.site.folder import Folder, rootFolder


import zope.intid
import zc.intid
import z3c.password.interfaces

from nti.dataserver import _Dataserver
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import session_storage
from nti.dataserver import containers as container
from nti.dataserver import intid_utility
from nti.dataserver import flagging
from nti.dataserver import shards as ds_shards
from nti.dataserver import password_utility


def install_chat( context ):
	pass


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

	# Set up the shard directory, and add this object to it
	# Shard objects contain information about the shard, including
	# object placement policies (?). They live in the main database
	shards = container.LastModifiedBTreeContainer()
	dataserver_folder['shards'] = shards
	shards[conn.db().database_name] = ds_shards.ShardInfo()
	assert conn.db().database_name != 'unnamed', "Must give a name"
	assert shards[conn.db().database_name].__name__


	# TODO: the 'users' key should probably be several different keys, one for each type of
	# Entity object; that way traversal works out much nicer and dataserver_pyramid_views is
	# simplified through dropping UserRootResource in favor of normal traversal
	install_root_folders( dataserver_folder )


	# Install the site manager and register components
	root['nti.dataserver_root'] = root_folder
	root['nti.dataserver'] = dataserver_folder

	oid_resolver =  _Dataserver.PersistentOidResolver()
	conn.add( oid_resolver )
	lsm.registerUtility( oid_resolver, provided=nti_interfaces.IOIDResolver )

	sess_storage = session_storage.OwnerBasedAnnotationSessionServiceStorage()
	lsm.registerUtility( sess_storage, provided=nti_interfaces.ISessionServiceStorage )

	intids = install_intids( dataserver_folder )

	everyone = dataserver_folder['users']['Everyone'] = users.Everyone()
	intids.register( everyone ) # Events didn't fire

	install_flag_storage( dataserver_folder )

	install_password_utility( dataserver_folder )

	return dataserver_folder

def install_intids( dataserver_folder ):
	lsm = dataserver_folder.getSiteManager()
	# A utility to create intids for any object that needs it
	# Two choices: With either one of them registered, subscribers
	# fire forcing objects to be adaptable to IKeyReference.
	# Int ids are not currently being used, but plans are for the
	# near future. A migration path will have to be established.
	#intids = zope.intid.IntIds( family=BTrees.family64 )
	intids = intid_utility.IntIds('_ds_intid', family=BTrees.family64 )
	intids.__name__ = '++etc++intids'
	intids.__parent__ = dataserver_folder
	lsm.registerUtility( intids, provided=zope.intid.IIntIds )
	# Make sure to register it as both types of utility, one is a subclass of the other
	lsm.registerUtility( intids, provided=zc.intid.IIntIds )
	return intids

def install_password_utility( dataserver_folder ):
	lsm = dataserver_folder.getSiteManager()
	policy = password_utility.HighSecurityPasswordUtility()
	policy.__name__ = '++etc++password_utility'
	policy.__parent__ = dataserver_folder
	policy.maxLength = 100
	policy.minLength = 6
	policy.groupMax = 10 # TODO: The group max interferes with pass phrases, which we like
	lsm.registerUtility( policy, provided=z3c.password.interfaces.IPasswordUtility )

def install_flag_storage( dataserver_folder ):
	lsm = dataserver_folder.getSiteManager()

	lsm.registerUtility( flagging.IntIdGlobalFlagStorage(), provided=nti_interfaces.IGlobalFlagStorage )

def install_root_folders( parent_folder,
						  folder_type=container.CaseInsensitiveLastModifiedBTreeFolder,
						  folder_names=('users', 'providers', 'quizzes'),  # TODO: Drop quizzes
						  extra_folder_names=(),
						  exclude_folder_names=() ):
	for key in set( ('users', 'providers', 'quizzes' ) + extra_folder_names) - set( exclude_folder_names ):
		parent_folder[key] = folder_type()
		parent_folder[key].__name__ = key

from nti.dataserver.interfaces import IShardLayout
def install_shard( root_conn, new_shard_name ):
	"""
	Given a root connection that is already modified to include a shard database
	connection having the given name, set up the datastructures for that new
	name to be a shard.
	"""
	# TODO: The tests for this live up in appserver/account_creation_views
	root_layout = IShardLayout( root_conn )
	shards = root_layout.shards
	if new_shard_name in shards:
		raise KeyError( "Shard already exists", new_shard_name )

	shard_conn = root_conn.get_connection( new_shard_name )
	shard_root = shard_conn.root()
	# TODO: Within this, how much of the site structure do we need/want to mirror?
	# Right now, I'm making the new dataserver_folder a child of the main root folder and giving it
	# a shard name. But I'm not setting up any site managers
	root_folder = root_layout.root_folder

	dataserver_folder = Folder()
	interface.alsoProvides( dataserver_folder, nti_interfaces.IDataserverFolder )
	shard_conn.add( dataserver_folder ) # Put it in the right DB
	shard_root['nti.dataserver'] = dataserver_folder
	# make it a child of the root folder (TODO: Yes? This gets some cross-db stuff into the root
	# folder, which may not be good. We deliberately avoided that for the 'shards' key)
	root_folder[new_shard_name] = dataserver_folder
	shards[new_shard_name] = ds_shards.ShardInfo()
	# Put the same things in there, but they must not take ownership or generate
	# events
	install_root_folders( dataserver_folder,
						  folder_type=container.EventlessLastModifiedBTreeContainer,
						  exclude_folder_names=('quizzes',) )
