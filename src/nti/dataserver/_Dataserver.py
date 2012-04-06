#!/usr/bin/env python
from __future__ import print_function, unicode_literals
import logging
logger = logging.getLogger( __name__ )

import os
import sys
import types
import inspect
import six

import collections

import gevent.local


from zope import interface
from zope import component
from zope.configuration import xmlconfig
from zope.event import notify
from zope.processlifetime import DatabaseOpenedWithRoot

import zope.generations.generations
import zope.deprecation


from persistent import Persistent, wref
import transaction

from persistent.mapping import PersistentMapping

import contextlib
from zope.component.hooks import site, getSite, setSite

import contenttypes
import datastructures
import sessions

import nti.apns as apns
from . import users
from . import interfaces
from . import ntiids
from . import chat_interfaces
from . import config


DEFAULT_PASSWORD = "temp001"

###
### Note: There is a bug is some versions of the python interpreter
### such that initiating ZEO connections at the module level
### results in a permanant hang: the interpreter has two threads
### that are both waiting on either the GIL or the import lock,
### but something forgot to release it. The solution is to move this
### into its own function and call it explicitly.
###

class InappropriateSiteError(LookupError): pass

class _Change(Persistent):

	def __init__( self, change, meta ):
		self.change = change
		self.meta = meta

	def __repr__( self ):
		return '_Change( %s, %s )' % (self.change, self.meta)

class _SessionDbMeetingStorage( object ):
	interface.implements(chat_interfaces.IMeetingStorage)

	def __init__( self, name ):
		"""
		:param string name: The name of the stored dict object.
		"""
		self.name = name

	def sdb(self):
		lsm = component.getSiteManager()
		conn = getattr( lsm, '_p_jar', None )
		if conn:
			# Our root is the top-level site manager we are using
			return conn.get_connection( 'Sessions' )
		#return _ContextManager.contextManager().conn.get_connection( 'Sessions' )

	def get( self, key ):
		return self.sdb().root()[self.name].get( key )

	def __getitem__( self, key ):
		return self.sdb().root()[self.name][key]

	def add_room( self, room ):
		self.sdb().root()[self.name].add_room( room )

	def __delitem__( self, k ):
		del self.sdb().root()[self.name][k]

	def __str__(self):
		return "<%s %s %s>" % ( self.__class__, self.name, hex(id(self)) )

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
		assert component.getSiteManager() == sitemanc.getSiteManager()
		assert component.getUtility( interfaces.IDataserver )
		yield sitemanc


def run_job_in_site(func, retries=0,
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
		Defaults to one.
	:return: The value returned by the first successful invocation of `func`.
	"""
	note = func.__doc__
	if note:
		note = note.split('\n', 1)[0]
	else:
		note = func.__name__

	with _connection_cm() as conn:
		for i in xrange(retries + 1):
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
			except transaction.interfaces.TransientError:
				t.abort()
				if i == retries:
					# We failed for the last time
					raise
			except transaction.interfaces.DoomedTransaction:
				raise
			except:
				t.abort()
				raise

interface.directlyProvides( run_job_in_site, interfaces.IDataserverTransactionRunner )

DATASERVER_DEMO = 'DATASERVER_DEMO' in os.environ and 'DATASERVER_NO_DEMO' not in os.environ


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
		component.provideUtility( self.conf )
		self.db, self.sessionsDB, self.searchDB = self._setup_dbs( parentDir, dataFileName, daemon )

		# Now, simply broadcasting the DatabaseOpenedWithRoot option
		# will trigger the installers/evolvers from zope.generations
		# TODO: Should we be the ones doing this?

		# In the past, we weren't used to install the application
		# Therefore we could have all the installed components, but
		# not the generation key. We'll support that for awhile by
		# manually running the migrations: set the version to 1, the first version that
		# actually was installed by us, and then let the 1-to-2 migration path
		# really fire.
		# We also need to arrange for the example database to get migrated
		# if it present (since we do not statically configure it)
		with self.db.transaction() as conn:
			root = conn.root()
			if root.get( zope.generations.generations.generations_key ) is None and root.get( 'users' ) is not None:
				# OK, the application has been run before, but migration and schema setup have
				# not.
				generations = PersistentMapping()
				root[zope.generations.generations.generations_key] = generations
				generations['nti.dataserver'] = 1
			generations = root.get( zope.generations.generations.generations_key )
			if generations is not None and 'nti.dataserver-example' in generations:
				# see config.py
				# TODO: Circular import
				import nti.dataserver.utils.example_database_initializer
				component.provideUtility(
					nti.dataserver.utils.example_database_initializer.ExampleDatabaseInitializer(),
					name='nti.dataserver-example' )



		notify( DatabaseOpenedWithRoot( self.db ) )

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

	@property
	def root(self):
		# We expect to be in a transaction and have a site manager
		# installed that came from the database
		lsm = component.getSiteManager()
		conn = getattr( lsm, '_p_jar', None )
		if conn:
			# Our root is the top-level site manager we are using
			return conn.root()['nti.dataserver'].getSiteManager()
		raise InappropriateSiteError( "Using Dataserver outside of site manager" )

	def close(self):
		def _c( n ):
			if hasattr( self, n ):
				try:
					getattr( self, n ).close()
				except AttributeError:
					logger.warning( 'Failed to close %s', n, exc_info=True )
		_c( 'searchDB' )
		_c( 'sessionsDB' )
		_c( 'db' )

	def get_by_oid( self, oid_string, ignore_creator=False ):
		resolver = component.queryUtility( interfaces.IOIDResolver )
		if resolver is None:
			logger.warn( "Using dataserver without a proper ISiteManager configuration." )
		return resolver.get_object_by_oid( oid_string, ignore_creator=ignore_creator ) if resolver else None

class Dataserver(MinimalDataserver):

	interface.implements(interfaces.IDataserver)

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

			# if 'Everyone' not in self.root['users']:
			# 	# Hmm. In the case that we're running multiple DS instances in the
			# 	# same VM, our constant could wind up with different _p_jar
			# 	# and _p_oid settings. Hence the copy
			# 	self.root['users']['Everyone'] = copy.deepcopy( users.EVERYONE )
			# This is interesting. Must do this to ensure that users
			# that get created at different times and that have weak refs
			# to the right thing. What's a better way?
			# TODO: This is almost certainly wrong given the _p_jar stuff
			users.EVERYONE = root['nti.dataserver'].getSiteManager()['users']['Everyone']


		room_name = 'meeting_rooms'

		self._setupPresence()
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

	def _setupPresence( self ):
		"""
		Hooks up the User's presence information to work with the actual
		online session info.
		"""
		def getPresence( s ):
			return "Online" if self.sessions.get_sessions_by_owner(s.username)\
				   else "Offline"

		# FIXME: This is horribly ugly
		users.User.presence = property(getPresence)

	def _setup_session_manager( self ):
		# The session service will read a component from our local site manager
		return sessions.SessionService()

	def _setup_chat( self, room_name ):
		# Delayed imports due to cycles
		import chat
		import meeting_container_storage
		return  chat.Chatserver( self.session_manager,
								 meeting_storage=_SessionDbMeetingStorage( room_name ),
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
		# Force the change to be added. Without this,
		# sometimes for some reason it doesn't get an OID by
		# the time the transaction is committed.
		self.root._p_jar.add( _change )
		# TODO: Reconsider this. It's probably not needed anymore,
		# and our choice of datastructure--a list--is terribly inefficient
		#self.root['changes'].append( _change )

		txn = transaction.get() #_ContextManager.contextManager().txn

		# Coalesce if possible
		adder = getattr( txn, 'add' + self._HOOK_NAME + 'Hook' )
		getter = getattr( txn, 'get' + self._HOOK_NAME + 'Hooks' )
		found = False
		for hook in getter():
			if isinstance( hook[0], Dataserver._OnCommit ):
				if hook[0].kwargs == kwargs:
					hook[0].add_change( _change )
					found = True
					break
		if not found:
			on_commit = Dataserver._OnCommit(self,_change,kwargs)
			adder( on_commit )

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
	def find_content_type( self, typeName=None ):
		"""
		Given the name of a type, optionally ending in 's' for
		plural, returns that type.
		"""
		className = typeName[0:-1] if typeName.endswith('s') else typeName
		result = None

		def find_class_in( mod, can_create=False ):
			clazz = mod.get( className )
			if not clazz and className.lower() == className:
				# case-insensitive search of loaded modules if it was lower case.
				for k in mod:
					if k.lower() == className:
						clazz = mod[k]
						break
			return clazz if getattr( clazz, '__external_can_create__', can_create ) else None

		result = find_class_in( contenttypes.__dict__, True ) or find_class_in( users.__dict__, False )
		# If not in the known packages, look across all NTI modules
		if not result:
			for k, v in sys.modules.iteritems():
				if k.startswith( 'nti.') and isinstance( v, types.ModuleType ):
					result = find_class_in( v.__dict__, False )
					if result: break

		return result

	def ensure_content_type_exists( self, typeName=None, _createMissing=True ):
		""" Given the name of a type, optionally ending in 's' for
		plural, returns that type. The type will be a class descending
		from contenttypes._UserContentRoot or IExternalObject. """
		result = self.find_content_type( typeName )

		if not result and _createMissing:
			className = typeName[0:-1] if typeName.endswith('s') else typeName
			# If there isn't one, we dynamically create it.
			# TODO: Think about this. This is largely for purposes of legacy tests.
			newType = type( className, (contenttypes._UserArbitraryDataContentRoot,), dict())
			newType.__module__ = contenttypes._UserArbitraryDataContentRoot.__module__
			contenttypes.__dict__[className] = newType
			result = newType

		return result

	def create_content_type( self, typeName=None, create_missing=True ):
		""" Given the name of a type, optionally ending in 's' for plural,
		returns a new instance of that type. The instance will
		be a class descending from contenttypes._UserContentRoot

		:param bool create_missing: If True (default) classes not found will be created.
		"""
		if not typeName: return None
		# _createMissing is internal to reduce code dup
		typ = self.ensure_content_type_exists( typeName, _createMissing=create_missing )
		# defend against None and other non-factories
		return typ() if callable( typ ) else None

	def get_external_type( self, externalObject, searchModules=(users,) ):
		""" Given an object with a Class attribute, find a type that corresponds to it. """
		# TODO: This really doesn't belong on the dataserver object.
		className = None
		try:
			if 'Class' not in externalObject: return None
			className = externalObject['Class']
		except TypeError: return None # int, etc

		for mod in searchModules:
			if isinstance( mod, basestring ):
				# TODO: Replace with zope.dottedname
				try:
					mod = __import__( mod, fromlist=['a'] )
				except ImportError:
					logger.exception( "Unable to import module for external type" )
					continue
			if className in mod.__dict__ and getattr( mod.__dict__[className], '__external_can_create__', False ):
				return mod.__dict__[className]
		return None

	def update_from_external_object( self, containedObject, externalObject ):
		""" :return: `containedObject` after updates from `externalObject`"""

		# Parse any contained objects
		# TODO: We're (deliberately?) not actually updating any contained
		# objects, we're replacing them. Is that right? We could check OIDs...
		# If we decide that's right, then the internals could be simplified by
		# splitting the two parts
		# TODO: Should the current user impact on this process?
		search_modules = {users, type(containedObject).__module__, 'nti.dataserver.contenttypes' }
		if isinstance( externalObject, collections.MutableMapping ):
			for k,v in externalObject.iteritems():
				typ = self.get_external_type( v, searchModules=search_modules )
				if typ:
					v = self.update_from_external_object( typ(), v )
					externalObject[k] = v
				elif isinstance( v, collections.MutableSequence ):
					tmp = []
					for i in v:
						typ = self.get_external_type( i, searchModules=search_modules)
						if typ:
							i = self.update_from_external_object( typ(), i )
						tmp.append( i )
					externalObject[k] = tmp
		elif isinstance( externalObject, collections.MutableSequence ):
			tmp = []
			for i in externalObject:
				typ = self.get_external_type( i, searchModules=search_modules)
				if typ:
					i = self.update_from_external_object( typ(), i )
				tmp.append( i )
			return tmp


		# Run the resolution steps on the external object
		if hasattr( containedObject, '__external_oids__'):
			for keyPath in containedObject.__external_oids__:
				# TODO: This version is very simple, generalize it
				externalObjectOid = externalObject.get( keyPath )
				if isinstance( externalObjectOid, basestring ):
					externalObject[keyPath] = self.get_by_oid( externalObjectOid )
				elif isinstance( externalObjectOid, collections.MutableSequence ):
					for i in range(0,len(externalObjectOid)):
						externalObjectOid[i] = self.get_by_oid( externalObjectOid[i] )
		if hasattr( containedObject, '__external_resolvers__'):
			for key, value in containedObject.__external_resolvers__.iteritems():
				if not externalObject.get( key ): continue
				# classmethods and static methods are implemented with descriptors,
				# which don't work when accessed through the dictionary in this way,
				# so we special case it so instances don't have to.
				if isinstance( value, classmethod ) or isinstance( value, staticmethod ):
					value = value.__get__( None, containedObject.__class__ )
				externalObject[key] = value( self, externalObject, externalObject[key] )

		if hasattr( containedObject, 'updateFromExternalObject' ) :
			# The signature may vary.
			argspec = inspect.getargspec( containedObject.updateFromExternalObject )
			if argspec.keywords or 'dataserver' in argspec.args:
				containedObject.updateFromExternalObject( externalObject, dataserver=self )
			else:
				logger.warn( 'Using old-style update for %s %s', type(containedObject), containedObject )
				containedObject.updateFromExternalObject( externalObject )
		return containedObject


_SynchronousChangeDataserver = Dataserver
zope.deprecation.deprecated('_SynchronousChangeDataserver',
							"Use plain Dataserver" )

class PersistentOidResolver(Persistent):
	interface.implements( interfaces.IOIDResolver )
	_p_jar = None
	def get_object_by_oid( self, oid_string, ignore_creator=False ):
		connection = self._p_jar
		if connection is None:
			# Damn! Try a fallback
			logger.warn( "Persistent object has no jar; connection closed?" )
			lsm = component.getSiteManager()
			connection = getattr( lsm, '_p_jar', None )

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

	oid_string, database_name = datastructures.fromExternalOID( oid_string )
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
