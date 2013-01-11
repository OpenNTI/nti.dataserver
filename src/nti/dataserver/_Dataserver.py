#!/usr/bin/env python
from __future__ import print_function, unicode_literals, absolute_import
logger = __import__( 'logging' ).getLogger( __name__ )

import os
import six
from urlparse import urlparse

import gevent.queue
import gevent.local

import ZODB.interfaces
from ZODB.interfaces import IConnection
import ZODB.POSException
import struct # Connection can throw struct.error unpacking an OID

from zope import interface
from zope import component
from zope.event import notify
from zope.processlifetime import DatabaseOpened, DatabaseOpenedWithRoot
import zope.generations.generations
import zope.deprecation
from zc import intid as zc_intid
from persistent import Persistent

import redis

from nti.externalization import oids
import nti.apns as apns
from nti.ntiids import ntiids
from nti.externalization import interfaces as ext_interfaces


from nti.dataserver import sessions
from nti.dataserver import interfaces

from nti.chatserver.chatserver import Chatserver
from . import meeting_container_storage
from . import meeting_storage

from . import config

from nti.deprecated import hiding_warnings as hiding_deprecation_warnings


###
### Note: There is a bug is some versions of the python interpreter
### such that initiating ZEO connections at the module level
### results in a permanant hang: the interpreter has two threads
### that are both waiting on either the GIL or the import lock,
### but something forgot to release it. The solution is to move this
### into its own function and call it explicitly.
###

from nti.dataserver.interfaces import InappropriateSiteError, SiteNotInstalledError


class _Change(Persistent):

	def __init__( self, change, meta ):
		super(_Change,self).__init__()
		self.change = change
		self.meta = meta

	def __repr__( self ):
		return '_Change( %s, %s )' % (self.change, self.meta)


from .site import _connection_cm
from .site import _site_cm
from .site import run_job_in_site
zope.deprecation.deprecated( _connection_cm.__name__,
							 'Moved to .site' )
zope.deprecation.deprecated( _site_cm.__name__,
							 'Moved to .site' )
zope.deprecation.deprecated( run_job_in_site.__name__,
							 'Moved to .site' )

DATASERVER_DEMO = 'DATASERVER_DEMO' in os.environ and 'DATASERVER_NO_DEMO' not in os.environ

@interface.implementer(interfaces.IShardLayout)
class MinimalDataserver(object):
	"""
	Represents the basic connections and nothing more.
	"""

	def __init__(self, parentDir="~/tmp", dataFileName="test.fs", classFactory=None, apnsCertFile=None, daemon=None  ):
		"""
		"""
		if classFactory:
			raise TypeError( "classFactory no longer supported" )

		if parentDir == "~/tmp" and 'DATASERVER_DIR' in os.environ:
			parentDir = os.environ['DATASERVER_DIR']
		if dataFileName == 'test.fs' and 'DATASERVER_FILE' in os.environ:
			dataFileName = os.environ['DATASERVER_FILE']
		parentDir = os.path.expanduser( parentDir )
		self.conf = config.temp_get_config( parentDir, demo=DATASERVER_DEMO )
		# TODO: We shouldn't be doing this, it should be passed to us
		component.getGlobalSiteManager().registerUtility( self.conf )
		self.redis = self._setup_redis( self.conf )
		# Although _setup_dbs returns a tuple, we don't actually want to hold a ref
		# to any database except the root database. All access to multi-databases
		# should go through an open connection.
		self.db, _, _ = self._setup_dbs( parentDir, dataFileName, daemon )

		# In zope, IDatabaseOpened is fired by XXX.
		# zope.app.appsetup.bootstrap.bootStrapSubscriber listens for
		# this event, and ensures that the database has a IRootFolder
		# object. Once that happens, then bootStrapSubscriber fires
		# IDatabaseOpenedWithRoot.

		# zope.generations installers/evolvers are triggered on IDatabaseOpenedWithRoot
		# We notify both in that same order (sometimes action is taken on IDatabaseOpened
		# which impacts how zope.generations does its work on OpenedWithRoot)

		# TODO: Should we be the ones doing this?

		notify( DatabaseOpened( self.db ) )
		notify( DatabaseOpenedWithRoot( self.db ) )
		#ZODB.Connection.resetCaches()
		self._parentDir = parentDir
		self._dataFileName = dataFileName

		for deprecated in ('_setup_storage', '_setup_launch_zeo', '_setup_storages'):
			meth = getattr( self, deprecated, None )
			if meth is not None: # pragma: no cover
				raise DeprecationWarning( deprecated + " is no longer supported. Remove your method " + str(meth) )

	def _setup_dbs( self, parentDir, dataFileName, daemon ):
		"""
		Creates the database connections. Returns a tuple (userdb, sessiondb, searchdb);
		The first object in the tuple is the root database, and all databases are arranged
		in a multi-database setup.
		"""
		db, ses_db, search_db = self.conf.connect_databases()
		return db, ses_db, search_db

	def _setup_redis( self, conf ):
		if not conf.main_conf.has_option( 'redis', 'redis_url' ):
			msg = "YOUR CONFIGURATION IS OUT OF DATE. Please install redis and then run nti_init_env --upgrade-outdated --write-supervisord"
			logger.warn( msg )
			raise DeprecationWarning( msg )

		redis_url = conf.main_conf.get( 'redis', 'redis_url' )
		parsed_url = urlparse( redis_url )
		if parsed_url.scheme == 'file':
			# Redis client doesn't natively understand file://, only redis://
			client = redis.StrictRedis( unix_socket_path=parsed_url.path ) # XXX Windows
		else:
			client = redis.StrictRedis.from_url( redis_url )
		interface.alsoProvides( client, interfaces.IRedisClient )
		component.getGlobalSiteManager().registerUtility( client, interfaces.IRedisClient )
		return client

	@property
	def root(self):
		# We expect to be in a transaction and have a site manager
		# installed that came from the database
		lsm = component.getSiteManager()
		# zope.keyreference installs an IConnection adapter that
		# can traverse the lineage. That's important if we're using a nested,
		# transient site manager
		conn = ZODB.interfaces.IConnection( lsm, None )
		if conn:
			return conn.root()['nti.dataserver']

		raise InappropriateSiteError( "Using Dataserver outside of site manager" )

	@property
	def root_connection(self):
		"Returns the connection to the root database, the one containing the shard map."
		return IConnection(self.root)

	@property
	def shards(self):
		"Returns the map of known database shards."
		return self.root['shards']

	dataserver_folder = root

	@property
	def users_folder(self):
		return self.dataserver_folder['users']

	def close(self):
		def _c( n, o ):
			try:
				if o is not None:
					o.close()
			except Exception:
				logger.warning( 'Failed to close %s', o, exc_info=True )
				raise

		for k,v in self.db.databases.items():
			_c( k, v )

	def get_by_oid( self, oid_string, ignore_creator=False ):
		resolver = component.queryUtility( interfaces.IOIDResolver )
		if resolver is None:
			logger.warn( "Using dataserver without a proper ISiteManager configuration." )
		return resolver.get_object_by_oid( oid_string, ignore_creator=ignore_creator ) if resolver else None


@interface.implementer(interfaces.IDataserver)
class Dataserver(MinimalDataserver):

	def __init__(self, parentDir = "~/tmp", dataFileName="test.fs", classFactory=None, apnsCertFile=None, daemon=None  ):
		super(Dataserver, self).__init__(parentDir, dataFileName, classFactory, apnsCertFile, daemon )
		self.changeListeners = []

		with self.db.transaction() as conn:
			root = conn.root()
			# Perform migrations
			# TODO: Adopt the standard migration package
			# TODO: For right now, we are also handling initialization until all code
			# is ported over
			if not root.has_key( 'nti.dataserver' ):
				raise Exception( "Creating DS against uninitialized DB. Test code?", str(root) )


		room_name = 'meeting_rooms'

		self.session_manager = self._setup_session_manager( )
		self.chatserver = self._setup_chat( room_name )

		self._apnsCertFile = apnsCertFile
		self._apns = self

		# A topic that broadcasts Change events
		self.changePublisherStream, self.other_closeables = self._setup_change_distribution()


	def _setup_change_distribution( self ):
		"""
		:return: A tuple of (changePublisherStream, [other closeables])
		"""
		# To handle changes synchronously, we execute them before the commit happens
		# so that their changes are added with the main changes

		changePublisherStream = gevent.queue.Queue()
		def read_generic_changes():
			try:
				while True:
					logger.debug( "Waiting to receive change %s", os.getpid() )
					msg = changePublisherStream.get()
					try:
						logger.debug( "Received change %s %s", msg, os.getpid() )
						self._on_recv_change( msg )
						logger.debug( "Done processing change %s", os.getpid() )
					except Exception:
						logger.exception( 'error reading change' )
			finally:
				logger.debug( "Done receiving changes! %s", os.getpid() )
		reader = gevent.spawn( read_generic_changes )

		return (changePublisherStream, (reader,))

	def _setup_session_manager( self ):
		# The session service will read a component from our local site manager
		return sessions.SessionService()

	def _setup_chat( self, room_name ):
		return  Chatserver( self.session_manager,
							 meeting_storage=meeting_storage.CreatorBasedAnnotationMeetingStorage(),
							 meeting_container_storage=meeting_container_storage.MeetingContainerStorage( ) )


	def _setup_apns( self, apnsCertFile ):
		_apns = apns.APNS( certFile=apnsCertFile )

		# Here we used to be using an inproc ZMQ socket to listen
		# for device feedback events. Now we are using zope.event to
		# distribute these. In the future, if we need to
		# push APNS connections off to a background process, we can either
		# include that code in the APNS server, or we can start proxying
		# event objects around.

		return _apns

	def get_sessions(self):
		return self.session_manager
	sessions = property( get_sessions )


	@property
	def apns(self):
		if self._apns is self:
			try:
				self._apns = self._setup_apns( self._apnsCertFile )
			except Exception:
				# Probably a certificate problem
				logger.warn( "Failed to create APNS connection. Notifications not available" )
				self._apns = None
		return self._apns


	def close(self):
		super(Dataserver,self).close( )
		for x in getattr( self, 'other_closeables', None ) or ():
			try:
				x.close()
			except (AttributeError, TypeError): pass
		self.other_closeables = ()

	def add_change_listener( self, listener ):
		""" Adds a listener (a callable object) for changes."""
		if listener and listener not in self.changeListeners:
			self.changeListeners.append( listener )

	def remove_change_listener( self, listener ):
		self.changeListeners.remove( listener )

	# Exists as a callable class so that we can coallesce changes to the
	# same kwargs. Top-level so we can trust isinstance
	class _OnCommit(object):
		def __init__(self,ds,_change,kwargs):
			self._changes = [_change]
			self.kwargs = dict(kwargs) # Must copy, these tend to be re-used.
			self.ds = ds

		def add_change( self, _change ):
			self._changes.append( _change )

		def __call__( self, worked=True ):
			# Worked defaults do True so that this can be used
			# as a before-commit hook, which passes no argument
			if not worked:
				logger.warning( 'Dropping change on failure to commit' )
			else:
				if self._changes:
					self.ds._on_recv_change( self._changes )
				else:
					logger.debug( "There were no OIDs to publish %s", os.getpid() )

				# We are a one-shot object. Changes go or they don't.
				self._changes = ()

		def __repr__(self):
			return "<%s.%s object at %s %s>" % (self.__class__.__module__, self.__class__.__name__, id(self), self.kwargs)

	_HOOK_NAME = 'BeforeCommit'

	def enqueue_change( self, change, **kwargs ):
		""" Distributes a change to all the queued listener functions.
		The change must be a Persistent object, or at least support __getstate__."""
		# Posting the change is somewhat tricky. Regular
		# pickle doesn't work if we have persistent objects
		# involved (it cannot pickle through the _p_jar and DB objects).
		# We really don't want to pickle those anyway,
		# we want to just send their OIDs--/if/ they are in the DB, and stable.
		# We can almost accomplish this through the use of the ObjectReader/Writer pair,
		# which is what the DB itself uses. It deals correctly with
		# cross db references, persistent objects that aren't, yet.
		# However, there are cases it breaks down, specifically with some types
		# of persistent object that aren't yet in the database. To solve that and other
		# ownership questions, we simply stuff the object in the database and
		# send its ID.
		_change = _Change( change, dict(kwargs) ) # Must copy, tend to be reused
		# In the past, we did this with an on-commit hook, but the hook may run
		# after our site configuration has been removed, so it's best to
		# do it immediately
		self._on_recv_change( (_change,) )

		# # Force the change to be added. Without this,
		# # sometimes for some reason it doesn't get an OID by
		# # the time the transaction is committed.
		# self.root._p_jar.add( _change )

	def _on_recv_change( self, msg ):
		"""
		Given a Change received, distribute it to all registered listeners.
		:param sequence msg: Sequence of _Change objects. For backwards compatibility,
			can also be a sequence of OID strings.
		"""

		for oid in msg:
			_change = self.get_by_oid( oid ) if isinstance(oid,six.string_types) else oid
			change = _change.change

			for changeListener in self.changeListeners:
				changeListener( self, change, **_change.meta )
				# Since we are doing this synchronously now, we
				# let the errors propagate so that they rollback the transaction
				# (Otherwise, we could wind up with half-committed, bad state)


_SynchronousChangeDataserver = Dataserver
zope.deprecation.deprecated('_SynchronousChangeDataserver',
							"Use plain Dataserver" )

@interface.implementer( ext_interfaces.IExternalReferenceResolver )
@component.adapter( object, basestring )
def ExternalRefResolverFactory( _, __ ):
	ds = component.queryUtility( interfaces.IDataserver )
	return _ExternalRefResolver( ds ) if ds else None

class _ExternalRefResolver(object):
	def __init__( self, ds ):
		self.ds = ds
	def resolve( self, oid ):
		return self.ds.get_by_oid( oid )


@interface.implementer( interfaces.IOIDResolver )
class PersistentOidResolver(Persistent):

	def get_object_by_oid( self, oid_string, ignore_creator=False ):
		connection = IConnection(self)
		return get_object_by_oid( connection, oid_string, ignore_creator=ignore_creator )

def get_object_by_oid( connection, oid_string, ignore_creator=False ):
	"""
	Given an object id string as found in an OID value
	in an external dictionary, returns the object in the `connection` that matches that
	id, or None.

	:param ignore_creator: If True, then creator access checks will be
		bypassed.
	"""
	# TODO: This is probably rife with possibilities for attack
	required_user_marker = connection
	required_user = None
	if ntiids.is_ntiid_of_type( oid_string, ntiids.TYPE_OID ):
		parts = ntiids.get_parts( oid_string )
		oid_string = parts.specific
		# The provider must be given. If it's the system user,
		# we'll ignore it. Otherwise, it must be checked. If it's not
		# present, then use a marker that will always fail.
		required_user = parts.provider or required_user_marker
	elif ntiids.is_valid_ntiid_string( oid_string ):
		# Hmm, valid but not an OID.
		logger.debug( "Failed to resolve non-OID NTIID %s", oid_string )
		return None

	oid_string, database_name, intid = oids.fromExternalOID( oid_string )
	if not oid_string:
		logger.debug( 'No OID string given' )
		return None

	__traceback_info__ = oid_string, database_name, intid
	try:
		if database_name:
			connection = connection.get_connection( database_name )

		# ZEO/FileStorage tends to rais KeyError here, and RelStorage can do that to.
		# RelStorage can also raise struct.error if the oid_string is not packed validly:
		# see ZODB.utils.u64.
		result = connection[oid_string]

		#if result is None and required_user not in (required_user_marker, interfaces.SYSTEM_USER_NAME):
			# TODO: Right here, we have a user. We couldn't find the object globally,
			# so it may have been moved. We need to get the user-local index
			# and ask it to find it.
			#pass

		if interfaces.IWeakRef.providedBy( result ):
			result = result()

		if result is not None and intid is not None:
			obj = component.getUtility( zc_intid.IIntIds ).getObject( intid )
			if obj is not result:
				raise KeyError( "Mismatch between intid %s and %s", intid, obj )

		if result is not None and not ignore_creator:
			creator = getattr( result, 'creator', None )
			creator_name = getattr( creator, 'username', creator )
			# Only the creator can access something it created.
			# Only the system user can access anything without a creator
			# (TODO: Should that change?)
			if creator_name != None: # must check
				if ntiids.escape_provider(creator_name) != required_user:
					result = None
			elif required_user and required_user not in (interfaces.SYSTEM_USER_NAME,interfaces.SYSTEM_USER_ID):
				result = None

		return result
	except (KeyError,UnicodeDecodeError,struct.error):
		logger.exception( "Failed to resolve oid '%s' using '%s'", oid_string.encode('hex'), connection )
		return None
