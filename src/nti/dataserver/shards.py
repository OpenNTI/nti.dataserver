#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects relating to database sharding.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import persistent

from zope import interface
from zope import component
from zope.site.site import SiteManagerContainer
from ZODB.interfaces import IConnection

from nti.dataserver import datastructures as ds
from nti.dataserver import interfaces as nti_interfaces

@interface.implementer(nti_interfaces.IShardInfo)
class ShardInfo(persistent.Persistent,ds.CreatedModDateTrackingObject,SiteManagerContainer):
	"""
	Something giving information about a database shard.

	Shards may be :class:`zope.component.interfaces.ISite`.

	.. note:: As you can see, there's much more that needs to be done to this,
		in addition to making use of the policies that might be installed for a specific
		shard by making it a Site. For example, we might want to lock certain shards to avoid putting
		new users in them; that state would need to be tracked here.
	"""

@interface.implementer(nti_interfaces.IShardLayout)
@component.adapter(IConnection)
class ShardLayout(object):
	"""
	An object with the knowledge of a dataserver (or shard) layout.
	"""

	def __init__( self, root ):
		"""
		:param root: The root object of a ZODB connection, or a connection itself.
		"""
		self.root = root.root() if IConnection.providedBy( root ) else root

	@property
	def dataserver_folder(self):
		return self.root['nti.dataserver']

	@property
	def users_folder(self):
		return self.dataserver_folder['users']

	@property
	def shards(self):
		return self.dataserver_folder.get('shards')

	@property
	def root_folder(self):
		return self.root.get( 'nti.dataserver_root' )

@interface.implementer(nti_interfaces.INewUserPlacer)
class TrivialShardPlacer(object):
	"""
	A user placement policy that puts the user directly in the root database.
	"""

	def placeNewUser( self, user, user_directory, shards ):
		logger.info( "Assigning new user %s to root shard", user.username )
		IConnection(user_directory).add( user )
		# No need to put it in the directory, that's about to happen

class AbstractShardPlacer(object):
	"""
	Base class for :class:`nti.dataserver.interfaces.INewUserPlacer` objects that
	will be placing users in particular named shards.
	"""

	def place_user_in_shard_named( self, user, user_directory, shard_name ):
		"""
		Place the given user in a shard having the given name.

		:return: A `True` value if we could place the user in the requested shard,
			otherwise a `False` value.
		"""
		if not user or not shard_name:
			return False

		root_conn = IConnection(user_directory)
		shard_conn = root_conn.get_connection( shard_name ) # TODO: Handling the case where we can't get a connection
		if shard_conn and shard_conn is not root_conn:
			logger.info( "Assigning new user %s to shard %s", user.username, shard_name )
			shard_conn.add( user )

			# Also put it in the root directory of this shard, so that this shard
			# can get GC'd without fear of losing users
			nti_interfaces.IShardLayout(shard_conn).users_folder[user.username] = user
			return True

@interface.implementer(nti_interfaces.INewUserPlacer)
class HashedShardPlacer(TrivialShardPlacer,AbstractShardPlacer):
	"""
	A user placement policy that maps the user into an existing shard
	based on the hash of the username. The root shard will never be used
	if there is at least one other possibility.

	.. note:: Because the pointer (from the root database to the shard
		database) stays accurate even if more shards are added, this
		policy is not *fragile* (so long as shard names do not change).
		However, it is also not *repeatable* as the database
		configuration changes.
	"""

	def placeNewUser(self, user, user_directory, shards ):
		# While the shards are the same, to get consistent results,
		# we need the buckets to be the same too. Which means we must sort them.
		shard_buckets = sorted(shards.keys())
		# Removing the root shard, if it's present, since we fallback to that
		# and we want to avoid going there
		try:
			shard_buckets.remove( IConnection(user_directory).db().database_name )
		except ValueError: pass

		if not shard_buckets:
			# We have no choice but to place in the root
			TrivialShardPlacer.placeNewUser( self, user, user_directory, shards )
		else:

			shard_name = shard_buckets[hash(user.username) % len(shard_buckets)]

			if not self.place_user_in_shard_named( user, user_directory, shard_name ):
				# Narf. Going to have to go back to the root conn
				# Note that we can't do that ourself, because the root shard uses a
				# 'users' container that fires events, and the user object is probably not
				# ready for that yet.
				logger.debug( "Failed to assign new user %s to shard %s out of %s", user.username, shard_name, shard_buckets )
				TrivialShardPlacer.placeNewUser( self, user, user_directory, shards )
