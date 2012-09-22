#!/usr/bin/env python
from __future__ import print_function, unicode_literals
logger = __import__( 'logging' ).getLogger( __name__ )

import os
import six
from urlparse import urlparse
import contextlib

import gevent.queue
import gevent.local

import ZODB.interfaces
import ZODB.POSException
from zope import interface
from zope import component
from zope.event import notify
from zope.processlifetime import DatabaseOpened, DatabaseOpenedWithRoot
import zope.generations.generations
import zope.deprecation
from persistent import Persistent, wref
import transaction
from zope.component.hooks import site

import redis

from nti.externalization import oids
import nti.apns as apns
from nti.ntiids import ntiids
from nti.externalization import interfaces as ext_interfaces
import nti.externalization.internalization

from nti.dataserver import sessions
from nti.dataserver import interfaces

from nti.chatserver.chatserver import Chatserver
from . import meeting_container_storage
from . import meeting_storage

from . import config

from nti.deprecated import hiding_warnings as hiding_deprecation_warnings
from nti.deprecated import deprecated

DEFAULT_PASSWORD = "temp001"

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
		self.change = change
		self.meta = meta

	def __repr__( self ):
		return '_Change( %s, %s )' % (self.change, self.meta)


@contextlib.contextmanager
def _trivial_db_transaction_cm():
	# TODO: This needs all the retry logic, etc, that we
	# get in the main app through pyramid_tm

	lsm = component.getSiteManager()
	conn = getattr( lsm, '_p_jar', None )
	if conn:
		logger.warn( 'Reusing existing component connection %s %s', lsm, conn )
		yield conn
		return

	ds = component.getUtility( interfaces.IDataserver )
	transaction.begin()
	conn = ds.db.open()
	# If we don't sync, then we can get stale objects that
	# think they belong to a closed connection
	# TODO: Are we doing something in the wrong order? Connection
	# is an ISynchronizer and registers itself with the transaction manager,
	# so we shouldn't have to do this manually
	# ... I think the problem was a bad site. I think this can go away.
	conn.sync()
	sitemanc = conn.root()['nti.dataserver']


	with site( sitemanc ):
		assert component.getSiteManager() == sitemanc.getSiteManager()
		assert component.getUtility( interfaces.IDataserver )
		try:
			yield conn
			transaction.commit()
		except:
			transaction.abort()
			raise
		finally:
			conn.close()

with hiding_deprecation_warnings():
	interface.directlyProvides( _trivial_db_transaction_cm, interfaces.IDataserverTransactionContextManager )


@contextlib.contextmanager
def _connection_cm():

	ds = component.getUtility( interfaces.IDataserver )
	conn = ds.db.open()
	try:
		yield conn
	finally:
		conn.close()

@contextlib.contextmanager
def _site_cm(conn):
	# If we don't sync, then we can get stale objects that
	# think they belong to a closed connection
	# TODO: Are we doing something in the wrong order? Connection
	# is an ISynchronizer and registers itself with the transaction manager,
	# so we shouldn't have to do this manually
	# ... I think the problem was a bad site. I think this can go away.
	#conn.sync()
	# In fact, it must go away; if we sync the conn, we lose the
	# current transaction
	sitemanc = conn.root()['nti.dataserver']

	with site( sitemanc ):
		if component.getSiteManager() != sitemanc.getSiteManager():
			raise SiteNotInstalledError( "Hooks not installed?" )
		if component.getUtility( interfaces.IDataserver ) is None:
			raise InappropriateSiteError()
		yield sitemanc


def run_job_in_site(func, retries=0, sleep=None,
					_connection_cm=_connection_cm, _site_cm=_site_cm):
	"""
	Runs the function given in `func` in a transaction and dataserver local
	site manager.
	:param function func: A function of zero parameters to run. If it has a docstring,
		that will be used as the transactions note. A transaction will be begun before
		this function executes, and committed after the function completes. This function may be rerun if
		retries are requested, so it should be prepared for that.
	:param int retries: The number of times to retry the transaction and execution of `func` if
		:class:`transaction.interfaces.TransientError` is raised when committing.
		Defaults to zero (so the job runs once).
	:return: The value returned by the first successful invocation of `func`.
	"""
	note = func.__doc__
	if note:
		note = note.split('\n', 1)[0]
	else:
		note = func.__name__

	with _connection_cm() as conn:
		for i in xrange(retries + 1):

			# Opening the connection registered it with the transaction manager as an ISynchronizer.
			# Ultimately this results in newTransaction being called on the connection object
			# at `transaction.begin` time, which in turn syncs the storage. However,
			# when multi-databases are used, the other connections DO NOT get this called on them
			# if they are implicitly loaded during the course of object traversal or even explicitly
			# loaded by name turing an active transaction. This can lead to extra read conflict errors
			# (particularly with RelStorage which explicitly polls for invalidations at sync time).
			# (Once a multi-db connection has been used, then the next time it would be sync'd. A multi-db
			# connection is associated with the same connection to another database for its lifetime, and
			# when open()'d will sync all other such connections. Corrollary: ALWAYS go through
			# a connection object to get access to multi databases; never go through the database object itself.)

			# As a workaround, we iterate across all the databases and sync them manually; this increases the
			# cost of handling transactions for things that do not use the other connections, but ensures
			# we stay nicely in sync.

			# JAM: 2012-09-03: With the database resharding, evaluating the need for this.
			# Disabling it.
			#for db_name, db in conn.db().databases.items():
			#	__traceback_info__ = i, db_name, db, func
			#	if db is None: # For compatibility with databases we no longer use
			#		continue
			#	c2 = conn.get_connection(db_name)
			#	if c2 is conn:
			#		continue
			#	c2.newTransaction()

			# Now fire 'newTransaction' to the ISynchronizers, including the root connection
			# This may result in some redundant fires to sub-connections.
			t = transaction.begin()
			if i:
				t.note("%s (retry: %s)" % (note, i))
			else:
				t.note(note)
			try:
				with _site_cm(conn):
					result = func()
					# Commit the transaction while the site is still current
					# so that any before-commit hooks run with that site
					# (Though this has the problem that after-commit hooks would have an invalid
					# site!)
					t.commit()
				# No errors, return the result
				return result
			except transaction.interfaces.TransientError as e:
				t.abort()
				if i == retries:
					# We failed for the last time
					raise
				logger.debug( "Retrying transaction %s on exception (try: %s): %s", func, i, e )
				if sleep is not None:
					gevent.sleep( sleep )
			except transaction.interfaces.DoomedTransaction:
				raise
			except ZODB.POSException.StorageError as e:
				if str(e) == 'Unable to acquire commit lock':
					# Relstorage locks. Who's holding it? What's this worker doing?
					# if the problem is some other worker this doesn't help much
					from nti.appserver._util import dump_stacks
					import sys
					body = '\n'.join(dump_stacks())
					print( body, file=sys.stderr )
				raise
			except:
				t.abort()
				raise

interface.directlyProvides( run_job_in_site, interfaces.IDataserverTransactionRunner )

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
		# We notify both in that order.

		# TODO: Should we be the ones doing this?

		notify( DatabaseOpened( self.db ) )
		notify( DatabaseOpenedWithRoot( self.db ) )
		#ZODB.Connection.resetCaches()
		self._parentDir = parentDir
		self._dataFileName = dataFileName


	def _setup_storage( self, zeo_addr, storage_name, blob_dir, shared_blob_dir=True ):
		raise Exception( "Setup_storage no longer supported" )

	def _setup_launch_zeo( self, clientPipe, path, args, daemon ):
		raise Exception( "Must launch ZEO first." )

	def _setup_storages( self, parentDir, dataFileName, daemon ):
		raise Exception( "Setup storages no longer supported" )

	__my_setup_storages = _setup_storages

	def _setup_dbs( self, parentDir, dataFileName, daemon ):
		"""
		Creates the database connections. Returns a tuple (userdb, sessiondb, searchdb).
		"""
		if self._setup_storages != self.__my_setup_storages:
			raise Exception( "Setup storages no longer supported:" + str( self._setup_storages ) )
		db, ses_db, search_db = self.conf.connect_databases()
		return db, ses_db, search_db

	def _setup_redis( self, conf ):

		if not conf.main_conf.has_option( 'redis', 'redis_url' ):
			logger.warn( "YOUR CONFIGURATION IS OUT OF DATE. Please install redis and then run nti_init_env --upgrade-outdated --write-supervisord" )
			return # .sessions.SessionService can go either way right now. Remove when everyone has upgraded

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
		return self.root._p_jar

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
				raise Exception( "Creating DS against uninitialized DB. Test code?" )


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

	###
	# Dealing with content types
	# TODO: This should be separated out
	###
	@deprecated()
	def find_content_type( self, typeName=None ):
		"""
		Given the name of a type, optionally ending in 's' for
		plural, returns that type.
		"""
		return nti.externalization.internalization.find_factory_for_class_name( typeName )

	@deprecated()
	def update_from_external_object( self, containedObject, externalObject ):
		return nti.externalization.internalization.update_from_external_object( containedObject, externalObject, context=self )



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

# nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.users' )
# nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.contenttypes' )
# nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.providers' )
# nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.classes' )
# nti.externalization.internalization.register_legacy_search_module( 'nti.dataserver.quizzes' )
# nti.externalization.internalization.register_legacy_search_module( 'nti.chatserver.messageinfo' )



class PersistentOidResolver(Persistent):
	interface.implements( interfaces.IOIDResolver )

	def get_object_by_oid( self, oid_string, ignore_creator=False ):
		# We live with the pylint warning about '_p_jar' not being found on persistent. We cannot
		# declare a class attribute with that name, because doing so overrides
		# the getter/setter pair defined in the cPersistence PyTypeObject structure that is Persistent
		# and we lose access to it
		connection = self._p_jar
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

	oid_string, database_name = oids.fromExternalOID( oid_string )
	if not oid_string:
		logger.debug( 'No OID string given' )
		return None
	try:
		if database_name: connection = connection.get_connection( database_name )
		result = connection[oid_string]
		#if result is None and required_user not in (required_user_marker, interfaces.SYSTEM_USER_NAME):
			# TODO: Right here, we have a user. We couldn't find the object globally,
			# so it may have been moved. We need to get the user-local index
			# and ask it to find it.
			#pass

		if isinstance(result, wref.WeakRef):
			result = result()


		if result is not None and not ignore_creator:
			creator = getattr( result, 'creator', None )
			creator_name = getattr( creator, 'username', creator )
			# Only the creator can access something it created.
			# Only the system user can access anything without a creator
			# (TODO: Should that change?)
			if creator_name != None: # must check
				if ntiids.escape_provider(creator_name) != required_user:
					result = None
			elif required_user and required_user != interfaces.SYSTEM_USER_NAME:
				result = None

		return result
	except (KeyError,UnicodeDecodeError):
		logger.exception( "Failed to resolve oid '%s' using '%s'", oid_string.encode('hex'), connection )
		return None
