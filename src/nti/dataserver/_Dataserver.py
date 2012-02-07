import logging
logger = logging.getLogger( __name__ )

import os
import tempfile
import sys
import types
import stat
import inspect
try:
	import cPickle as pickle
except ImportError:
	import pickle

import warnings
import copy
import collections

import gevent.local

from gevent_zeromq import zmq

import ZODB
from zope import interface
from zope import component
from zope.configuration import xmlconfig
import ZODB.serialize
from zope.event import notify
from zope.processlifetime import DatabaseOpenedWithRoot
import zope.generations.generations

import ZEO
import ZEO.ClientStorage
from persistent import Persistent, wref
import transaction
from transaction.interfaces import DoomedTransaction
from persistent.mapping import PersistentMapping
from BTrees import OOBTree

import contenttypes
import datastructures
import sessions

import nti.apns as apns
import _daemonutils as daemonutils
from . import users
from . import _PubSubDevice
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

class _Change(Persistent):

	def __init__( self, change, meta ):
		self.change = change
		self.meta = meta

	def __repr__( self ):
		return '_Change( %s, %s )' % (self.change, self.meta)

class _ContextManager(object):
	"""
	PEP 343 context manager. Instances of this class must
	always be used with the same datasource.
	"""
	local = gevent.local.local()

	def __init__( self, db ):
		self.db = db
		self.tm = None
		self.conn = None
		self.txn = None
		self.doomed = None
		self._premature_exit_ok = False

	def __enter__(self):
		""" :return: The opened connection. """
		if hasattr( self.local, 'contextManager' ):
			raise ValueError( 'Transaction already entered' )

		self.local.contextManager = self
		self.tm = transaction.TransactionManager()
		self.conn = self.db.open( self.tm )
		self.txn = self.tm.begin()
		return self.conn

	def __exit__(self, t, v, tb):
		# Cannot exit twice.
		try:
			del self.local.contextManager
		except AttributeError:
			# except if otherwise designated
			if self._premature_exit_ok:
				return
			else:
				if t:
					raise t, v, tb
				raise

		try:
			if self.doomed:
				self.tm.abort()
				raise self.doomed[0], self.doomed[1], self.doomed[2]

			if t is None:
				try:
					self.tm.commit()
				except DoomedTransaction:
					self.tm.abort()
			else:
				self.tm.abort()
		finally:
			try:
				self.conn.close()
			except:
				self.tm.abort()
				self.conn.close()
			finally:
				self.conn = None
				self.tm = None
				self.txn = None

	def premature_exit_but_its_okay(self):
		self._premature_exit_ok = True
		self.__exit__( None, None, None )

	def root(self):
		return self.conn.root()

	@classmethod
	def contextManager(cls):
		""" Returns the thread-local context manager, if there is one. """
		try:
			return cls.local.contextManager
		except AttributeError:
			return None

class _NestedContextManager(object):
	"""
	Piggybacks on a parent context manager.
	"""

	def __init__( self, parent=None ):
		self.parent = parent
		self.doomed = None
		self.db = None
		self.tm = None
		self.conn = None
		self.txn = None

	def __enter__(self):
		if self.parent:
			self.db = self.parent.db
			self.tm = self.parent.tm
			self.conn = self.parent.conn
			self.txn = self.parent.txn
			return self.conn.root()

	def root( self ):
		return self.conn.root()

	def __exit__(self, t, v, tb):
		if t is not None:
			if self.parent:
				self.parent.doomed = (t, v, tb)

	def premature_exit_but_its_okay( self ):
		if callable( getattr( self.parent, 'premature_exit_but_its_okay', None ) ):
			self.parent.premature_exit_but_its_okay()

class _SessionDbMeetingStorage( object ):
	interface.implements(chat_interfaces.IMeetingStorage)

	def __init__( self, name ):
		"""
		:param string name: The name of the stored dict object.
		"""
		self.name = name

	def sdb(self):
		return _ContextManager.contextManager().conn.get_connection( 'Sessions' )

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



DATASERVER_DEMO = 'DATASERVER_DEMO' in os.environ and 'DATASERVER_NO_DEMO' not in os.environ

def _run_change_listener( parentDir, dataFileName, func_module, func_name, *func_args ):
	change_func = daemonutils.load_func( func_module, func_name )

	dataserver = _ChangeReceivingDataserver( parentDir, dataFileName )
	# TODO: This is something of a hack
	xmlconfig.file( 'configure.zcml', package=sys.modules['nti.dataserver'] )
	component.provideUtility( dataserver )
	logger.info( "Running change daemon %s %s", change_func, func_args )
	try:
		change_func( dataserver, *func_args )
	except:
		logger.exception( "Failed to install change listener" )
		sys.exit( 2 ) # 2 being a magic number that zdaemon knows not to restart us

	try:
		dataserver._change_reader.join()
	except:
		logger.exception( "Error joining change reader" )
		raise
	else:
		logger.info( "Shutting down change daemon %s %s", change_func, func_args )

from zope.deprecation import deprecate
@deprecate("Handle with config")
def spawn_change_listener( dataserver, func, args=() ):
	my_args = [dataserver._parentDir, dataserver._dataFileName, func.__module__, func.__name__]
	my_args.extend( args )
	daemonutils.launch_python_function_as_daemon( _run_change_listener, my_args,
												  directory=my_args[0],
												  qualifier=my_args[1] + func.__module__ + '.' + func.__name__ )

def temp_env_run_change_listener( change_func, *func_args ):
	dataserver = _ChangeReceivingDataserver()
	# TODO: This is something of a hack
	xmlconfig.file( 'configure.zcml', package=sys.modules['nti.dataserver'] )
	component.provideUtility( dataserver )
	logger.info( "Running change daemon %s %s", change_func, func_args )
	try:
		change_func( dataserver, *func_args )
	except:
		logger.exception( "Failed to install change listener" )
		sys.exit( 2 ) # 2 being a magic number that zdaemon knows not to restart us

	try:
		dataserver._change_reader.join()
	except:
		logger.exception( "Error joining change reader" )
		raise
	else:
		logger.info( "Shutting down change daemon %s %s", change_func, func_args )


class _ClassFactory(object):

	def __init__( self, classFactory, dbClassFactory ):
		self._classFactory = classFactory
		self._dbClassFactory = dbClassFactory

	def __call__( self, connection, modulename, globalname ):
		result = None

		if modulename.startswith( 'dataserver' ):
			modulename = 'nti.' + modulename
		try:
			result = self._classFactory( connection, modulename, globalname )
		except:
			pass
		if result is None:
			# The built-in factory returns 'Broken'
			# instances. See ZODB.broken.
			#if modulename == contenttypes.__name__:
			#	result = self.ensure_content_type_exists( globalname )
			#else:
			result = self._dbClassFactory( connection, modulename, globalname )

		return result

class MinimalDataserver(object):
	"""
	Represents the basic connections and nothing more.
	"""

	def __init__(self, parentDir="~/tmp", dataFileName="test.fs", classFactory=None, apnsCertFile=None, daemon=None  ):
		""" If classFactory is given, it is a callable of (connection, modulename, globalname) that
		should return a type; if it returns None or raises, the rest of the chain of factories
		will be traversed. Our version of the classFactory will auto-create missing contenttypes. """

		if parentDir == "~/tmp" and 'DATASERVER_DIR' in os.environ:
			parentDir = os.environ['DATASERVER_DIR']
		if dataFileName == 'test.fs' and 'DATASERVER_FILE' in os.environ:
			dataFileName = os.environ['DATASERVER_FILE']
		parentDir = os.path.expanduser( parentDir )
		self.conf = config.temp_get_config( parentDir, demo=DATASERVER_DEMO )
		# TODO: We shouldn't be doing this, it should be passed to us
		component.provideUtility( self.conf )
		self.db, self.sessionsDB, self.searchDB = self._setup_dbs( parentDir, dataFileName, daemon, classFactory )

		# Now, simply broadcasting the DatabaseOpenedWithRoot option
		# will trigger the installers/evolvers from zope.generations
		# TODO: Should we be the ones doing this?

		# In the past, we weren't used to install the application
		# Therefore we could have all the installed components, but
		# not the generation key. We'll support that for awhile by
		# manually running the migrations: set the version to 1, the first version that
		# actually was installed by us, and then let the 1-to-2 migration path
		# really fire.
		with self.db.transaction() as conn:
			root = conn.root()
			if root.get( zope.generations.generations.generations_key ) is None and root.get( 'users' ) is not None:
				# OK, the application has been run before, but migration and schema setup have
				# not.
				generations = PersistentMapping()
				root[zope.generations.generations.generations_key] = generations
				generations['nti.dataserver'] = 1


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

	def _setup_dbs( self, parentDir, dataFileName, daemon, classFactory ):
		"""
		Creates the database connections. Returns a tuple (userdb, sessiondb, searchdb).
		"""
		if self._setup_storages != self.__my_setup_storages:
			raise Exception( "Setup storages no longer supported:" + str( self._setup_storages ) )
		db, ses_db, search_db = self.conf.connect_databases()
		db.classFactory = _ClassFactory( classFactory, db.classFactory )
		ses_db.classFactory = _ClassFactory( classFactory, ses_db.classFactory )

		return db, ses_db, search_db

	@property
	def root(self):
		return _ContextManager.contextManager().conn.root()

	def dbTrans( self ):
		""" Returns a context manager that wraps a transaction. """
		cm = _ContextManager.contextManager()
		if cm:
			# TODO: Should we automatically nest or make that explicit?
			cm = _NestedContextManager( cm )
		else:
			cm = _ContextManager( self.db )
		return cm

	def doom( self ):
		_ContextManager.contextManager().tm.doom()

	def commit( self ):
		cm = _ContextManager.contextManager()

		if cm is not None and cm.tm is not None:
			cm.tm.commit()

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


	def __del__(self):
		self.close()

	def get_by_oid( self, oid_string, ignore_creator=False ):
		return get_object_by_oid( _ContextManager.contextManager().conn, oid_string, ignore_creator=ignore_creator )

class Dataserver(MinimalDataserver):

	interface.implements(interfaces.IDataserver)

	def __init__(self, parentDir = "~/tmp", dataFileName="test.fs", classFactory=None, apnsCertFile=None, daemon=None  ):
		""" If classFactory is given, it is a callable of (connection, modulename, globalname) that
		should return a type; if it returns None or raises, the rest of the chain of factories
		will be traversed. Our version of the classFactory will auto-create missing contenttypes. """
		super(Dataserver, self).__init__(parentDir, dataFileName, classFactory, apnsCertFile, daemon )
		self.changeListeners = []

		with self.dbTrans( ) as conn:
			# Perform migrations
			# TODO: Adopt the standard migration package
			# TODO: For right now, we are also handling initialization until all code
			# is ported over
			if not self.root.has_key( 'users' ):
				raise Exception( "Creating DS against uninitialized DB. Test code?" )

			# if 'Everyone' not in self.root['users']:
			# 	# Hmm. In the case that we're running multiple DS instances in the
			# 	# same VM, our constant could wind up with different _p_jar
			# 	# and _p_oid settings. Hence the copy
			# 	self.root['users']['Everyone'] = copy.deepcopy( users.EVERYONE )
			# This is interesting. Must do this to ensure that users
			# that get created at different times and that have weak refs
			# to the right thing. What's a better way?
			users.EVERYONE = self.root['users']['Everyone']

			self.migrateUsers( self.root['users'] )

		# Sessions and Chat configuration
		def sdb():
			db = self
			class CM(object):
				def __init__(self):
					self._cm = None
					self.conn = None
				def __enter__(self):
					self._cm = db.dbTrans()
					self._cm.__enter__()
					self.conn = self._cm.conn
					return self.conn.get_connection( 'Sessions' ).root()
				def __exit__( self, t, v, tb ):
					self._cm.__exit__( t, v, tb )

			return CM()


		room_name = 'meeting_rooms'

		self._setupPresence()
		self.session_manager = self._setup_session_manager( sdb )
		self.chatserver = self._setup_chat( room_name )

		self._apnsCertFile = apnsCertFile
		self._apns = self

		# A topic that broadcasts Change events
		self.changePublisherStream, self.other_closeables = self._setup_change_distribution()

	def _setup_change_distribution( self ):
		# We only broadcast, we never receive.
		# TODO: Some of this could be shared.
		# A topic that broadcasts Change events
		changePublisher, _ = self.conf.create_pubsub_pair( 'changes', connect_sub=False )

		changePublisherStream = gevent.queue.Queue()

		def write_generic_change( ):
			try:
				while True:
					msg = changePublisherStream.get()
					try:
						logger.debug( "ZMQ distributing change message %s %s", msg, os.getpid() )
						changePublisher.send_multipart( msg )
					except Exception:
						logger.exception( 'error sending change %s' )
			finally:
				logger.debug( "Stopping sending ZMQ changes %s", os.getpid() )

		writer = gevent.spawn( write_generic_change )

		return (changePublisherStream, (changePublisher, writer))

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

	def _setup_session_manager( self, sdb ):
		return sessions.SessionService( sdb )

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
		#Dataserver.dataserver = None

	def __del__(self):
		self.close()

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
				oids = {datastructures.toExternalOID( _change ) for _change in self._changes
						if datastructures.toExternalOID(_change)}
				if oids:
					oids = list(oids)
					logger.debug( "Enqueuing change OIDs %s in %s(%s)", oids, os.getpid(), self )
					try:
						self.ds.changePublisherStream.put_nowait( oids )
					except:
						logger.exception( "Failed to put changes to the queue %s", os.getpid() )
						raise
				else:
					logger.debug( "There were no OIDs to publish %s", os.getpid() )

				if len(oids) != len(self._changes):
					logger.warning( 'Dropping non-externalized change on the floor!' )

				# We are a one-shot object. Changes go or they don't.
				self._changes = []

		def __repr__(self):
			return "<%s.%s object at %s %s>" % (self.__class__.__module__, self.__class__.__name__, id(self), self.kwargs)

	_HOOK_NAME = 'AfterCommit'

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
		_ContextManager.contextManager().conn.add( _change )
		self.root['changes'].append( _change )

		txn = _ContextManager.contextManager().txn

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
		""" Given a Change received, distribute it to all registered listeners. """

		done = False
		tries = 5
		while tries and not done:
			try:
				with self.dbTrans() as conn:
					conn._storage_sync()
					for oid in msg:
						_change = self.get_by_oid( oid )
						change = _change.change

						for changeListener in self.changeListeners:
							try:
								changeListener( self, change, **_change.meta )
							except Exception as e:
								logger.exception( "Failed to distribute change to %s", changeListener )
				done = True
				break
			except transaction.interfaces.TransientError as e:
				logger.warn( "Retrying to distribute change", exc_info=True )
				tries -= 1
				# Give things a chance to settle.
				gevent.sleep( 0.5 )
			except Exception as e:
				logger.exception( "Failed to distribute change" )
				break

		if not done:
			logger.warning( "Failed to distribute change %s", msg )

	def find_content_type( self, typeName=None ):
		""" Given the name of a type, optionally ending in 's' for
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


	def migrateUsers( self, usersContainer ):

		logger.info( 'migrating users %s', len(usersContainer) )
		# Because we are mutating the container, and
		# all of the methods like keys() and iterkeys()
		# are dynamic, they stop iteration prematurely.
		# Thus we must materialize the set of keys
		# before we begin to get everything.

		if getattr( usersContainer['Everyone'], 'creator', '') != 'zope.security.management.system_user':
			usersContainer['Everyone'].creator = 'zope.security.management.system_user'

		for key in list(usersContainer.keys()):
			try:
				o = usersContainer[key]
			except KeyError: continue
			if getattr( o, 'lastModified', None ) == 0:
				o.lastModified = 42
			cs = getattr( o, 'containersOfShared', None )
			if cs is not None and not hasattr( cs, 'set_ids' ):
				cs.set_ids = False
				logger.info( "Updated containersOfShared on %s", key )
			try:
				everyone = o.friendsLists['Everyone']
				if getattr( o.friendsLists['Everyone'], 'creator', '') != 'zope.security.management.system_user':
					delattr( o.friendsLists['Everyone'], 'creator' )
					logger.info( "Updated everyone for %s", key )
			except (KeyError,AttributeError):
				pass
			except Exception:
				logger.exception( "Failed to update %s", key )

		logger.info( 'done migrating users' )

class _SynchronousChangeDataserver(Dataserver):
	""" A dataserver that processes changes synchronously. """

	_HOOK_NAME = 'BeforeCommit'

	def _setup_change_distribution( self ):
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
		self._change_reader = reader # TODO: Hack to keep alive

		return (changePublisherStream, ())

class _ChangeReceivingDataserver(Dataserver):

	def _setup_change_distribution( self ):
		changePublisher, changeSubscriber = self.conf.create_pubsub_pair( 'changes' )

		def read_generic_changes():
			try:
				while True:
					logger.debug( "Waiting to receive change %s", os.getpid() )
					msg = changeSubscriber.recv_multipart()
					try:
						logger.debug( "Received change %s %s", msg, os.getpid() )
						self.db.invalidateCache()
						self._on_recv_change( msg )
						logger.debug( "Done processing change %s", os.getpid() )
					except Exception:
						logger.exception( 'error reading change' )
			finally:
				logger.debug( "Done receiving changes! %s", os.getpid() )
		reader = gevent.spawn( read_generic_changes )
		self._change_reader = reader # TODO: Hack

		changePublisherStream = gevent.queue.Queue()

		def write_generic_change( ):
			while True:
				msg = changePublisherStream.get()
				try:
					changePublisher.send_multipart( msg )
				except Exception:
					logger.exception( 'error sending change' )

		writer = gevent.spawn( write_generic_change )

		return (changePublisherStream, (changePublisher, changeSubscriber, reader, writer))

	# These are all things we don't need to do, because we can
	# assume they are done by the main processes. The background
	# process doesn't need to spawn any other daemons.

	def _setup_launch_zeo( self, clientPipe, path, args, daemon ):
		pass

	def migrateUsers( self, usersContainer ):
		pass

	def _setupPresence( self ):
		pass

	# sessions and chat are required in the background processes
	# to dispatch change notifications to connected sessions.
	# TODO: Clean this up a bit, this tries to launch pub-sub
	# processes.


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
