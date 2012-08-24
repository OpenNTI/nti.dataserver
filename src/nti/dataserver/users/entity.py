#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import


logger = __import__( 'logging' ).getLogger( __name__ )

import functools
import urllib

from zope import interface
from zope import component
from zope.event import notify
import zope.schema.interfaces

from zope import lifecycleevent
from zope.keyreference.interfaces import IKeyReference

from zope.annotation import interfaces as an_interfaces

from repoze.lru import lru_cache

import persistent
import ZODB.POSException
from ZODB.interfaces import IConnection

from nti.ntiids import ntiids


import nti.externalization.internalization

from nti.dataserver import datastructures

from nti.dataserver import interfaces as nti_interfaces
import nti.apns.interfaces
from . import interfaces

from nti.externalization.datastructures import InterfaceObjectIO


def _get_shared_dataserver(context=None,default=None):
	if default != None:
		return component.queryUtility( nti_interfaces.IDataserver, context=context, default=default )
	return component.getUtility( nti_interfaces.IDataserver, context=context )


@lru_cache(10000)
def _lower(s): return s.lower() if s else s


@functools.total_ordering
@interface.implementer( nti_interfaces.IEntity, nti_interfaces.ILastModified, an_interfaces.IAttributeAnnotatable)
class Entity(persistent.Persistent,datastructures.CreatedModDateTrackingObject):
	"""
	The root for things that represent human-like objects.
	"""

	_ds_namespace = 'users' # TODO: This doesn't really belong here

	@classmethod
	def get_entity( cls, username, dataserver=None, default=None, _namespace=None ):
		"""
		Returns an existing entity with the given username or None. If the
		dataserver is not given, then the global dataserver will be used.

		:param basestring username: The username to find. If this string is actually
			an ntiid, then an entity will be looked up by ntiid. This permits
			finding user-specific objects like friends lists.
		"""

		if ntiids.is_valid_ntiid_string( username ):
			result = ntiids.find_object_with_ntiid( username )
			if result is not None:
				if not isinstance(result,Entity):
					result = None
				return result or default


		# Allow for escaped usernames, since they are hard to defend against
		# at a higher level (this behaviour changed in pyramid 1.2.3)
		username = urllib.unquote( username )
		dataserver = dataserver or _get_shared_dataserver(default=default)
		if dataserver is not default:
			return dataserver.root[_namespace or cls._ds_namespace].get( username, default )
		return default

	@classmethod
	def create_entity( cls, dataserver=None, **kwargs ):
		"""
		Creates (and returns) and places in the dataserver a new entity,
		constructed using the keyword arguments given, the same as those
		the User constructor takes. If an user already exists with that name,
		raises a :class:`KeyError`. You handle the transaction.

		The newly-created user will be placed in a shard through use of a
		:class:`nti.dataserver.interfaces.INewUserPlacer`. If the unnamed (default)
		utility is available, it will be used. Otherwise, the utility named
		``default`` (which is configured by this package) will be used.

		:keyword dict external_value: Optional dictionary used to update the object
			through the user externalization mechanisms. This is done
			before the user is stored anywhere and any added/created events are
			fired. No notifications are emitted during this process.
		"""

		dataserver = dataserver or _get_shared_dataserver()
		root_users = dataserver.root[cls._ds_namespace]
		if 'parent' not in kwargs:
			kwargs['parent'] = root_users

		# When we auto-create users, we need to be sure
		# they have a database connection so that things that
		# are added /to them/ (their contained storage) in the same transaction
		# will also be able to get a database connection and hence
		# an OID.
		# NOTE: This is also where we decide which database shard the user lives in
		# First we create the skeleton object
		user = cls.__new__( cls )
		user.username = kwargs['username']
		# Then we place it in a database. It's important to do this before any code
		# runs so that subobjects which might go looking through their parents
		# to find a IConnection find the user's IConnection *first*, before they find
		# the `root_users` connection
		placer = component.queryUtility( nti_interfaces.INewUserPlacer ) or component.getUtility( nti_interfaces.INewUserPlacer, name='default' )
		placer.placeNewUser( user, root_users, dataserver.shards )

		IKeyReference( user ) # Ensure it gets added to the database
		assert getattr( user, '_p_jar', None ), "User should have a connection"

		# Finally, we init the user
		ext_value = kwargs.pop( 'external_value', None )
		user.__init__( **kwargs )
		assert getattr( user, '_p_jar', None ), "User should still have a connection"

		# Notify we're about to update
		notify( interfaces.WillUpdateNewEntityEvent( user ) )

		# Update from the external value, if provided
		if ext_value:
			nti.externalization.internalization.update_from_external_object( user, ext_value, context=dataserver, notify=False )

		lifecycleevent.created( user ) # Fire created event
		# Must manually fire added event if parent was given
		if kwargs['parent'] is not None:
			lifecycleevent.added( user, kwargs['parent'], user.username )

		# Now store it. If there was no parent given or parent was none,
		# this will fire ObjectAdded. If parent was given and is different than root_users,
		# this will fire ObjectMoved. If the user already exists, raises a KeyError
		root_users[user.username] = user

		return user

	@classmethod
	def delete_entity( cls, username, dataserver=None ):
		"""
		Delete the entity (in this class's namespace) given by `username`. If the entity
		doesn't exist, raises :class:`KeyError`.
		:return: The user that was deleted.
		"""
		dataserver = dataserver or _get_shared_dataserver()
		root_users = dataserver.root[cls._ds_namespace]

		user = root_users[username]
		del root_users[username]

		# Also clean it up from whatever shard it happened to come from
		home_shard = nti_interfaces.IShardLayout( IConnection( user ) )
		if username in home_shard.users_folder:
			del home_shard.users_folder[username]
		return user

	creator = nti_interfaces.SYSTEM_USER_NAME
	__parent__ = None

	def __init__(self, username,
				 parent=None):
		super(Entity,self).__init__()
		if not username or not username.strip():
			# Throw a three-arg version, similar to what a Field would do
			raise zope.schema.interfaces.InvalidValue( "Username must be non-blank", 'Username', username )
		if '%' in username or ',' in username: # TODO: Spaces?
			# % is illegal because we sometimes have to
			# URL encode an @ to %40. Comma we reserve as a separator
			raise zope.schema.interfaces.InvalidValue( "Username contains invalid characters", 'Username', username )


		self.username = username

		# Entities, and in particular Principals, have a created time,
		# and their last modified date is initialized to this created
		# time...this implies there are never temporary objects of this type
		# and that this type represents a fully formed object after construction
		self.createdTime = self.updateLastMod()

		if parent is not None:
			# If we pre-set this, then the ObjectAdded event doesn't
			# fire (the ObjectCreatedEvent does). On the other hand, we can't add anything to friendsLists
			# if an intid utility is installed if we don't have a parent (and thus
			# cannot be adapted to IKeyReference).
			self.__parent__ = parent


	def _get__name__(self):
		return self.username
	def _set__name__(self,new_name):
		if new_name:
			# Deleting from a container wants to remove our name.
			# We cannot allow that.
			self.username = new_name
	__name__ = property(_get__name__, _set__name__ )


	def __repr__(self):
		try:
			return '%s(%r,%r,%r)' % (self.__class__.__name__,self.username, self.realname, self.alias)
		except (ZODB.POSException.ConnectionStateError,AttributeError):
			# This most commonly (only?) comes up in unit tests when nose defers logging of an
			# error until after the transaction has exited. There will
			# be other log messages about trying to load state when connection is closed,
			# so we don't need to try to log it as well
			return object.__repr__(self)

	def __str__(self):
		try:
			return self.username
		except ZODB.POSException.ConnectionStateError:
			return object.__str__(self)

	@property
	def id(self):
		""" Our ID is a synonym for our username"""
		return self.username

	### Externalization ###

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		# Profile info
		profile_iface = interfaces.IUserProfileSchemaProvider( self ).getSchema()
		profile = profile_iface( self )
		InterfaceObjectIO( profile, profile_iface ).updateFromExternalObject( parsed, *args, **kwargs )

	### Comparisons and Hashing ###

	def __eq__(self, other):
		try:
			return other is self or _lower(self.username) == _lower(other.username)
		except AttributeError:
			return NotImplemented

	def __lt__(self, other):
		try:
			return _lower(self.username) < _lower(other.username)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return _lower(self.username).__hash__()
