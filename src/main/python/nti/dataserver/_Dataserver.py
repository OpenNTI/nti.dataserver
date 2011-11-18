import logging
logger = logging.getLogger( __name__ )

import os
import tempfile
import sys
import types
import stat
try:
	import cPickle as pickle
except ImportError:
	import pickle

import traceback
import warnings
import copy
import collections

import gevent.local

try:
	from gevent_zeromq import zmq
except ImportError:
	print 'WARN: Please check Dependencies.txt and install updates'
	import zmq

import ZODB
from zope import interface
import ZODB.serialize
from ZODB import DemoStorage
import ZEO
from persistent import Persistent, wref

from ZEO import ClientStorage
import transaction
from persistent.list import PersistentList

import contenttypes
import datastructures
import sessions

import nti.apns as apns
import _daemonutils as daemonutils
from . import users
from . import _PubSubDevice
from . import interfaces




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
			else: raise

		try:
			if self.doomed:
				self.tm.abort()
				raise self.doomed

			if t is None:
				self.tm.commit()
			else:
				self.tm.abort()
		finally:
			try:
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
			traceback.print_exc()
			if self.parent:
				self.parent.doomed = t

	def premature_exit_but_its_okay( self ):
		if callable( getattr( self.parent, 'premature_exit_but_its_okay', None ) ):
			self.parent.premature_exit_but_its_okay()

class _SessionDbDictWrapper( object ):
	"""
	An object that looks like a dict. Piggybacks on the current transaction
	established by the _ContextManager and uses the "Sessions" connection, which
	must contain a real dict-like object under a given name.
	"""
	def __init__( self, name ):
		"""
		:param string name: The name of the stored dict object.
		"""
		self.name = name

	def sdb(self):
		return _ContextManager.contextManager().conn.get_connection( 'Sessions' )

	def get( self, key, defv=None ):
		return self.sdb().root()[self.name].get( key, defv )

	def __getitem__( self, key ):
		return self.sdb().root()[self.name][key]

	def __setitem__( self, k, v ):
		conn = self.sdb()
		conn.root()[self.name][k] = v
		if hasattr( v, '_p_jar' ) and getattr( v, '_p_jar', self ) is None:
			# ensure it gets an OID right now
			conn.add( v )

	def __delitem__( self, k ):
		del self.sdb().root()[self.name][k]

	def __str__(self):
		return "<%s %s %s>" % ( self.__class__, self.name, hex(id(self)) )

	def keys( self ):
		return self.sdb().root()[self.name].keys()


DATASERVER_DEMO = 'DATASERVER_DEMO' in os.environ and 'DATASERVER_NO_DEMO' not in os.environ

def _get_change_pubsub_addrs( parentDir, dataFileName ):
	"""
	:return: Tuple (pub_addr, sub_addr, flag_file)
	"""
	pub_sub_dir = parentDir
	pub_sub_dir = os.path.expanduser( pub_sub_dir )

	pub_sub_file = 'change.' + dataFileName
	pub_file = 'pub.' + pub_sub_file
	sub_file = 'sub.' + pub_sub_file

	pub_path = os.path.join( pub_sub_dir, pub_file )
	pub_addr = 'ipc://' + pub_path
	sub_path = os.path.join( pub_sub_dir, sub_file )
	sub_addr = 'ipc://' + sub_path

	flag_file = os.path.join( pub_sub_dir, 'pub.sub.flag.' + pub_sub_file )

	return (pub_addr,sub_addr,flag_file)

def _run_change_listener( parentDir, dataFileName, func_module, func_name, *func_args ):
	change_func = daemonutils.load_func( func_module, func_name )

	dataserver = _ChangeReceivingDataserver( parentDir, dataFileName )
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


def spawn_change_listener( dataserver, func, args=() ):
	my_args = [dataserver._parentDir, dataserver._dataFileName, func.__module__, func.__name__]
	my_args.extend( args )
	daemonutils.launch_python_function_as_daemon( _run_change_listener, my_args,
												  directory=my_args[0],
												  qualifier=my_args[1] + func.__module__ + '.' + func.__name__ )

class MinimalDataserver(object):
	"""
	Represents the basic connections and nothing more.
	"""

	dataserver = None
	@classmethod
	def get_shared_dataserver(cls):
		return cls.dataserver

	def __init__(self, parentDir = "~/tmp", dataFileName="test.fs", classFactory=None, apnsCertFile=None, daemon=None  ):
		""" If classFactory is given, it is a callable of (connection, modulename, globalname) that
		should return a type; if it returns None or raises, the rest of the chain of factories
		will be traversed. Our version of the classFactory will auto-create missing contenttypes. """
		if parentDir == "~/tmp" and 'DATASERVER_DIR' in os.environ:
			parentDir = os.environ['DATASERVER_DIR']
		if dataFileName == 'test.fs' and 'DATASERVER_FILE' in os.environ:
			dataFileName = os.environ['DATASERVER_FILE']
		parentDir = os.path.expanduser( parentDir )
		self.db, self.sessionsDB, self.searchDB = self._setup_dbs( parentDir, dataFileName, daemon, classFactory )
		MinimalDataserver.dataserver = self
		self._parentDir = parentDir
		self._dataFileName = dataFileName


	def _setup_storage( self, zeo_addr, storage_name, blob_dir, shared_blob_dir=True ):
		storage = ZEO.ClientStorage.ClientStorage( zeo_addr, storage=storage_name, blob_dir=blob_dir, shared_blob_dir=shared_blob_dir )
		assert ZODB.interfaces.IBlobStorage in interface.providedBy(storage), "Should be supporting blobs"

		return storage

	def _setup_launch_zeo( self, clientPipe, path, args, daemon ):
		daemonutils.launch_python_daemon( clientPipe, path, args, daemon=daemon )

	def _setup_storages( self, parentDir, dataFileName, daemon ):
		"""
		Ensures that ZEO is running, configuring it with the needed file storages.
		:return: A tuple of results from :meth:`_setup_storage`: (user, session, search)
		"""

		if 'INSTANCE_HOME' not in os.environ:
			os.environ['INSTANCE_HOME'] = parentDir
			try:
				os.mkdir( os.path.join( parentDir, 'var' ) )
			except: pass

		clientDir = os.path.expanduser( parentDir )
		if not os.path.exists( clientDir ):
			os.mkdir( clientDir )

		clientPipe = clientDir + "/zeosocket"
		dataFile = clientDir + "/" + dataFileName
		blobDir = dataFile + '.blobs'
		if not os.path.exists( blobDir ):
			os.mkdir( blobDir )
			os.chmod( blobDir, stat.S_IRWXU )

		sessionDataFile = os.path.join( clientDir, 'sessions.' + dataFileName )
		sessionBlobDir = os.path.join( clientDir, 'sessions.' + dataFileName + '.blobs' )

		searchDataFile = os.path.join( clientDir, 'search.' + dataFileName )
		searchBlobDir = os.path.join( clientDir, 'search.' + dataFileName + '.blobs' )

		configuration = """
			<zeo>
			address %(clientPipe)s
			</zeo>
			<filestorage 1>
			path %(dataFile)s
			blob-dir %(blobDir)s
			</filestorage>
			<filestorage 2>
			path %(sessionDataFile)s
			blob-dir %(sessionBlobDir)s
			</filestorage>
			<filestorage 3>
			path %(searchDataFile)s
			blob-dir %(searchBlobDir)s
			</filestorage>


			<eventlog>
			<logfile>
			path %(logfile)s
			format %%(asctime)s %%(message)s
			level DEBUG
			</logfile>
			</eventlog>
			""" % { 'clientPipe': clientPipe, 'blobDir': blobDir,
					'dataFile': dataFile, 'logfile': clientDir + '/zeo.log',
					'sessionDataFile': sessionDataFile, 'sessionBlobDir': sessionBlobDir,
					'searchDataFile': searchDataFile, 'searchBlobDir': searchBlobDir
					}
		shared_blobs = True # While we are on IPC
		if DATASERVER_DEMO:
			logger.info( "Creating demo storages" )
			# NOTE: DemoStorage is NOT a ConflictResolvingStorage.
			# It will not run our _p_resolveConflict methods.
			for i in range(1,4):
				configuration = configuration.replace( '<filestorage %s>' % i,
													   '<demostorage %s>\n\t\t\t<filestorage %s>' % (i,i) )
			configuration = configuration.replace( '</filestorage>', '</filestorage>\n\t\t</demostorage>' )
			# Must use non-shared blobs, DemoStorage is missing fshelper.
			shared_blobs = False
			blobDir = tempfile.mkdtemp( '.demoblobs', prefix='blobs' )
			sessionBlobDir = tempfile.mkdtemp( '.demoblobs', prefix='session' )
			searchBlobDir = tempfile.mkdtemp( '.demoblobs', prefix='search' )
			# TODO: We need to clean these up
			logger.debug( "Using temporary blob dirs %s %s %s", blobDir, sessionBlobDir, searchBlobDir )
		config_file = clientDir + '/configuration.xml'
		daemonutils.write_configuration_file( config_file, configuration )

		path = os.path.dirname( ZEO.__file__ ) + "/runzeo.py"
		args = ['-C', config_file]
		self._setup_launch_zeo( clientPipe, path, args, daemon )

		return ( self._setup_storage( clientPipe, '1', blobDir, shared_blob_dir=shared_blobs ),
				 self._setup_storage( clientPipe, '2', sessionBlobDir, shared_blob_dir=shared_blobs ),
				 self._setup_storage( clientPipe, '3', searchBlobDir, shared_blob_dir=shared_blobs ) )

	def _setup_dbs( self, parentDir, dataFileName, daemon, classFactory ):
		"""
		Creates the database connections. Returns a tuple (userdb, sessiondb, searchdb).
		"""

		st_user, st_sess, st_search = self._setup_storages( parentDir, dataFileName, daemon )
		databases = {}
		db = ZODB.DB( st_user, databases=databases, database_name='Users' )
		dbClassFactory = db.classFactory
		# TODO: There's some duplication of code here
		def find_global( connection, modulename, globalname ):
			result = None

			if modulename.startswith( 'dataserver' ):
				modulename = 'nti.' + modulename
			try:
				result = classFactory( connection, modulename, globalname )
			except:
				pass
			if result is None:
				# The built-in factory returns 'Broken'
				# instances. See ZODB.broken.
				#if modulename == contenttypes.__name__:
				#	result = self.ensure_content_type_exists( globalname )
				#else:
				result = dbClassFactory( connection, modulename, globalname )

			return result
		db.classFactory = find_global
		sessionsDB = ZODB.DB( st_sess,
							  databases=databases,
							  database_name='Sessions')
		dbClassFactory2 = db.classFactory
		def find_global2( connection, modulename, globalname ):
			result = None

			if modulename.startswith( 'dataserver' ):
				modulename = 'nti.' + modulename
			try:
				result = classFactory( connection, modulename, globalname )
			except:
				pass
			if result is None:
				# The built-in factory returns 'Broken'
				# instances. See ZODB.broken.
				result = dbClassFactory2( connection, modulename, globalname )

			return result
		sessionsDB.classFactory = find_global2

		searchDB = ZODB.DB( st_search,
							databases=databases,
							database_name='Search')
		return (db, sessionsDB, searchDB)


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

	@classmethod
	def dsTrans( cls ):
		return cls.get_shared_dataserver().dbTrans()

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
					warnings.warn( 'Failed to close %s' % n )
		_c( 'searchDB' )
		_c( 'sessionsDB' )
		_c( 'db' )


	def __del__(self):
		self.close()

	def get_by_oid( self, oid_string ):
		return get_object_by_oid( _ContextManager.contextManager().conn, oid_string )



class Dataserver(MinimalDataserver):

	interface.implements(interfaces.IDataserver)

	# dataserver = None
	# @classmethod
	# def get_shared_dataserver(cls):
	# 	return cls.dataserver

	def __init__(self, parentDir = "~/tmp", dataFileName="test.fs", classFactory=None, apnsCertFile=None, daemon=None  ):
		""" If classFactory is given, it is a callable of (connection, modulename, globalname) that
		should return a type; if it returns None or raises, the rest of the chain of factories
		will be traversed. Our version of the classFactory will auto-create missing contenttypes. """
		super(Dataserver, self).__init__(parentDir, dataFileName, classFactory, apnsCertFile, daemon )

		Dataserver.dataserver = self
		# TODO: Who should be responsible for that?

		with self.dbTrans( ):
			self.changeListeners = []

			if not self.root.has_key('users'):
				self.root['users'] = datastructures.CaseInsensitiveModDateTrackingOOBTree()
			if 'Everyone' not in self.root['users']:
				# Hmm. In the case that we're running multiple DS instances in the
				# same VM, our constant could wind up with different _p_jar
				# and _p_oid settings. Hence the copy
				self.root['users']['Everyone'] = copy.deepcopy( users.EVERYONE )
			# This is interesting. Must do this to ensure that users
			# that get created at different times and that have weak refs
			# to the right thing. What's a better way?
			users.EVERYONE = self.root['users']['Everyone']

			# By keeping track of changes in one specific place, and weak-referencing
			# them elsewhere, we can control how much history is kept in one place.
			# This also solves the problem of 'who owns the change?' We do.
			if not self.root.has_key( 'changes'):
				self.root['changes'] = PersistentList()

			for key in ('vendors', 'library', 'quizzes', 'providers' ):
				if not self.root.has_key( key ):
					self.root[key] = datastructures.CaseInsensitiveModDateTrackingOOBTree()
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


		room_name = 'chat_rooms'
		tran_name = 'transcripts'
		with sdb() as r:
			for x in (room_name, tran_name):
				if x not in r:
					r[x] = datastructures.CaseInsensitiveModDateTrackingOOBTree()

		self._setupPresence()
		self.session_manager = self._setup_session_manager( sdb )
		self.chatserver = self._setup_chat( room_name, tran_name )

		self._apns = self._setup_apns( apnsCertFile )

		# A topic that broadcasts Change events
		self.changePublisherStream, self.other_closeables = self._setup_change_distribution()

	def _setup_change_distribution( self ):
		# We only broadcast, we never receive.
		# TODO: Some of this could be shared.
		pub_addr, sub_addr, flag_file = _get_change_pubsub_addrs( self._parentDir, self._dataFileName )

		daemonutils.launch_python_daemon( flag_file, _PubSubDevice.__file__, [flag_file, pub_addr, sub_addr] )

		# A topic that broadcasts Change events
		changePublisher = zmq.Context.instance().socket( zmq.PUB )
		changePublisher.connect( sub_addr )

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

		users.User.presence = property(getPresence)

	def _setup_session_manager( self, sdb ):
		return sessions.SessionService( sdb )

	def _setup_chat( self, room_name, tran_name ):
		# Delayed imports due to cycles
		import chat
		import meeting_container_storage
		return  chat.Chatserver( self.session_manager,
								 meeting_storage=_SessionDbDictWrapper( room_name ),
								 transcript_storage=_SessionDbDictWrapper( tran_name ),
								 meeting_container_storage=meeting_container_storage.MeetingContainerStorage( self ) )


	def _setup_apns( self, apnsCertFile ):
		_apns = apns.APNS( certFile=apnsCertFile )

		# Listen for feedback about bad devices and send
		# them to the Users class
		apnsFeedbackSocket = zmq.Context.instance().socket( zmq.SUB )
		# TODO: A registry for these
		apnsFeedbackSocket.connect( 'inproc://apns.feedback' )
		apnsFeedbackSocket.setsockopt( zmq.SUBSCRIBE, "" )

		def read_from_apns():
			while True:
				msg = apnsFeedbackSocket.recv_multipart()
				# Notice that even though the server used send_pyobj, the zmqstream gets a
				# multi-message object with raw content. We must unpickle the first part.
				try:
					users.User.onDeviceFeedback( self, pickle.loads( msg[0] ) )
				except Exception:
					logger.exception( 'Error reading from apns feedback' )
		gevent.spawn( read_from_apns )

		return _apns

	def get_sessions(self):
		return self.session_manager
	sessions = property( get_sessions )


	@property
	def apns(self):
		return self._apns


	@classmethod
	def dsTrans( cls ):
		return cls.get_shared_dataserver().dbTrans()


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

		def __call__( self, worked ):
			if not worked:
				logger.warning( 'Dropping change on failure to commit' )
			else:
				oids = {datastructures.toExternalOID( _change ) for _change in self._changes
						if datastructures.toExternalOID(_change)}
				if oids:
					oids = list(oids)
					logger.debug( "Enqueuing change OIDs %s %s", oids, os.getpid() )
					try:
						self.ds.changePublisherStream.put_nowait( oids )
					except:
						logger.exception( "Failed to put changes to the queue %s", os.getpid() )
						raise
				else:
					logger.debug( "There were no OIDs to publish %s", os.getpid() )

				if len(oids) != len(self._changes):
					logger.warning( 'Dropping non-externalized change on the floor!' )

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
		found = False
		for hook in txn.getAfterCommitHooks():
			if isinstance( hook[0], Dataserver._OnCommit ):
				if hook[0].kwargs == kwargs:
					hook[0].add_change( _change )
					found = True
					break
		if not found:
			on_commit = Dataserver._OnCommit(self,_change,kwargs)
			txn.addAfterCommitHook( on_commit )

	def _on_recv_change( self, msg ):
		""" Given a Change received, distribute it to all registered listeners. """

		done = False
		tries = 5
		while tries and not done:
			try:
				with self.dbTrans():
					for oid in msg:
						_change = self.get_by_oid( oid )
						change = _change.change

						for changeListener in self.changeListeners:
							try:
								changeListener( self, change, **_change.meta )
							except Exception, e:
								logger.exception( "Failed to distribute change to %s", changeListener )
				done = True
				break
			except transaction.interfaces.TransientError as e:
				logger.exception( "Retrying to distribute change" )
				tries -= 1
				# Give things a chance to settle.
				# TODO: Is this right?
				self.db.invalidateCache()
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
		return typ() if type else None

	def get_external_type( self, externalObject, searchModules=(users,) ):
		""" Given an object with a Class attribute, find a type that corresponds to it. """
		className = None
		try:
			if 'Class' not in externalObject: return None
			className = externalObject['Class']
		except TypeError: return None # int, etc

		for mod in searchModules:
			if isinstance( mod, basestring ):
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
			# The signature may vary. See if it will take us:
			try:
				containedObject.updateFromExternalObject( externalObject, dataserver=self )
			except TypeError, e:
				if e.message == "updateFromExternalObject() got an unexpected keyword argument 'dataserver'":
					logger.debug( 'Using old-style update for %s %s', type(containedObject), containedObject )
					containedObject.updateFromExternalObject( externalObject )
				else:
					raise
		return containedObject


	def migrateUsers( self, usersContainer ):

		logger.info( 'migrating users %s', len(usersContainer) )
		# Because we are mutating the container, and
		# all of the methods like keys() and iterkeys()
		# are dynamic, they stop iteration prematurely.
		# Thus we must materialize the set of keys
		# before we begin to get everything.

		for key in list(usersContainer.keys()):
			try:
				o = usersContainer[key]
			except KeyError: continue
			if getattr( o, 'lastModified', None ) == 0:
				o.lastModified = 42

		logger.info( 'done migrating users' )


class _ChangeReceivingDataserver(Dataserver):

	def _setup_change_distribution( self ):
		pub_addr, sub_addr, flag_file = _get_change_pubsub_addrs( self._parentDir, self._dataFileName )
		# We can assume that the pub sub device is running.
		# daemonutils.launch_python_daemon( flag_file, _PubSubDevice.__file__, [flag_file, pub_addr, sub_addr] )

		# A topic that broadcasts Change events
		changePublisher = zmq.Context.instance().socket( zmq.PUB )
		changePublisher.connect( sub_addr )
		changeSubscriber = zmq.Context.instance().socket( zmq.SUB )
		changeSubscriber.setsockopt( zmq.SUBSCRIBE, "" )
		changeSubscriber.connect( pub_addr )

		def read_generic_changes():
			try:
				while True:
					logger.debug( "Waiting to receive change %s", os.getpid() )
					msg = changeSubscriber.recv_multipart()
					try:
						logger.debug( "Received change %s %s", msg, os.getpid() )
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

	def _setup_apns( self, apnsCertFile ):
		pass

	# sessions and chat are required in the background processes
	# to dispatch change notifications to connected sessions.
	# TODO: Clean this up a bit, this tries to launch pub-sub
	# processes.


def get_object_by_oid( connection, oid_string ):
	"""
	Given an object id string as found in an OID value
	in an external dictionary, returns the object in the `connection` that matches that
	id, or None.
	"""
	# TODO: This is probably rife with possibilities for attack
	oid_string, database_name = datastructures.fromExternalOID( oid_string )
	try:
		if database_name: connection = connection.get_connection( database_name )
		result = connection[oid_string]
		if isinstance(result, wref.WeakRef):
			result = result()
		return result
	except KeyError:
		logger.exception( "Failed to resolve oid '%s' using '%s'", oid_string, connection )
		return None
