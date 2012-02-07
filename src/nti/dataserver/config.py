#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import os
import sys
import stat
import ConfigParser
from ConfigParser import SafeConfigParser

from zope import interface
from nti.dataserver import interfaces as nti_interfaces
from gevent_zeromq import zmq # If things crash, remove core.so


def _file_contents_equal( path, contents ):
	""" :return: Whether the file at `path` exists and has `contents` """
	result = False
	if os.path.exists( path ):
		with open( path, 'rU', 1 ) as f:
			path_contents = f.read()
			result = path_contents.strip() == contents.strip()

	return result

def write_configuration_file( path, contents ):
	""" Ensures the contents of `path` contain `contents`. """
	if not _file_contents_equal( path, contents ):
		# Must make the file
		logger.debug( 'Writing config file %s', path )
		try:
			os.mkdir( os.path.dirname( path ) )
		except OSError: pass
		with open( path, 'w' ) as f:
			print( contents, file=f )

class _Program(object):
	cmd_line = None
	name = None
	priority = 999

	def __init__( self, name, cmd_line=None ):
		self.name = name
		if cmd_line is None:
			cmd_line = name
		self.cmd_line = cmd_line

	def get_command(self):
		return self.cmd_line

	def set_command(self, value):
		self.cmd_line = value
	command = property(get_command, set_command)

class _ReadableEnv(object):
	interface.implements(nti_interfaces.IEnvironmentSettings)
	env_root = '/'
	settings = {}
	programs = ()

	def __init__( self, root='/', settings=None ):
		self.env_root = os.path.expanduser( root )
		self.settings = settings if settings is not None else dict(os.environ)
		self.programs = []
		self._main_conf = None

	@property
	def main_conf(self):
		if self._main_conf is None:
			self._main_conf = ConfigParser.SafeConfigParser()
			self._main_conf.read( self.conf_file( 'main.ini' ) )
		return self._main_conf

	def conf_file( self, name ):
		return os.path.join( self.env_root, 'etc', name )

	def run_dir( self ):
		return os.path.join( self.env_root, 'var' )

	def run_file( self, name ):
		return os.path.join( self.run_dir(), name )

	def data_file( self, name ):
		return os.path.join( self.env_root, 'data', name )

	def log_file( self, name ):
		return os.path.join( self.env_root, 'var', 'log', name )

	def _create_pubsub_pair(self, pub_addr, sub_addr, connect_sub=True, connect_pub=True):
		pub_socket = zmq.Context.instance().socket( zmq.PUB )
		if connect_pub:
			pub_socket.connect( sub_addr )

		sub_socket = zmq.Context.instance().socket( zmq.SUB )
		sub_socket.setsockopt( zmq.SUBSCRIBE, b"" )
		if connect_sub:
			sub_socket.connect( pub_addr )

		return pub_socket, sub_socket

	def create_pubsub_pair( self, section_name, connect_sub=True, connect_pub=True ):
		"""
		:return: A pair of ZMQ sockets (pub, sub), connected as specified.
		"""
		return self._create_pubsub_pair( self.main_conf.get( section_name, 'pub_addr' ),
										 self.main_conf.get( section_name, 'sub_addr' ),
										 connect_sub=connect_sub,
										 connect_pub=connect_pub )

class _Env(_ReadableEnv):

	def __init__( self, root='/', settings=None, create=False ):
		super(_Env,self).__init__( root=root, settings=settings )
		if create:
			os.makedirs( self.env_root )
			os.makedirs( self.run_dir() )
			os.makedirs( os.path.join( self.run_dir() , 'log' ) )

	def get_programs(self):
		return self.programs

	def add_program( self, program ):
		self.programs.append( program )

	def write_main_conf( self ):
		if self._main_conf is not None:
			with open( self.conf_file( 'main.ini' ), 'wb' ) as fp:
				self._main_conf.write(fp)

	def write_conf_file( self, name, contents ):
		write_configuration_file( self.conf_file( name ), contents )

	def write_supervisor_conf_file( self, pserve_ini):

		ini = ConfigParser.SafeConfigParser()
		ini.add_section( 'supervisord' )
		ini.set( 'supervisord', 'logfile', self.log_file( 'supervisord.log' ) )
		ini.set( 'supervisord', 'loglevel', 'debug' )
		ini.set( 'supervisord', 'pidfile', self.run_file( 'supervisord.pid' ) )
		ini.set( 'supervisord', 'childlogdir', self.run_file( 'log' ) )

		ini.add_section( 'unix_http_server' )
		ini.set( 'unix_http_server', 'file', self.run_file( 'supervisord.sock' ) )

		ini.add_section( 'supervisorctl' )
		ini.set( 'supervisorctl', 'serverurl', 'unix://' + self.run_file( 'supervisord.sock' ) )

		ini.add_section( 'rpcinterface:supervisor' )
		ini.set( 'rpcinterface:supervisor', 'supervisor.rpcinterface_factory', 'supervisor.rpcinterface:make_main_rpcinterface' )

		for p in self.programs:
			line = 'program:%s' % p.name
			ini.add_section( line )
			ini.set( line, 'command', p.cmd_line)
			if p.priority != _Program.priority:
				ini.set( line, 'priority', str(p.priority) )
			ini.set( line, 'environment', 'DATASERVER_DIR=%(here)s/../' )

		with open( self.conf_file( 'supervisord.conf' ), 'wb' ) as fp:
			ini.write( fp )

		command = 'pserve'
		ini.add_section( 'program:pserve' )
		ini.set( 'program:pserve', 'command', '%s %s' % (command, pserve_ini) )
		ini.set( 'program:pserve', 'environment', 'DATASERVER_DIR=%(here)s/../' )
		ini.set( 'supervisord', 'nodaemon', 'true' )
		with open( self.conf_file( 'supervisord_dev.conf' ), 'wb' ) as fp:
			ini.write( fp )

def _configure_pubsub( env, name ):

	pub_file = env.run_file( 'pub.%s.sock' % name )
	sub_file = env.run_file( 'sub.%s.sock' % name )
	pid_file = env.run_file( 'pubsub.%s.pid' % name )

	cmd_line = ' '.join( ['nti_pubsub_device', pid_file, 'ipc://' + pub_file, 'ipc://' + sub_file ] )

	env.add_program( _Program( 'pubsub_%s' % name, cmd_line ) )

	if not env.main_conf.has_section( name ):
		env.main_conf.add_section( name )
	env.main_conf.set( name, 'pub_addr', 'ipc://' + pub_file )
	env.main_conf.set( name, 'sub_addr', 'ipc://' + sub_file )

def _configure_pubsub_changes( env ):

	_configure_pubsub( env, 'changes' )

def _configure_pubsub_session( env ):
	_configure_pubsub( env, 'session' )

def _configure_zeo( env_root ):
	"""
	:return: A list of URIs that can be passed to db_from_uris to directly connect
	to the file storages, without using ZEO.
	"""
	def _mk_blobdir( blobDir ):
		if not os.path.exists( blobDir ):
			os.makedirs( blobDir )
			os.chmod( blobDir, stat.S_IRWXU )


	def _mk_blobdirs( datafile ):
		blobDir = datafile + '.blobs'
		_mk_blobdir( blobDir )
		demoblobDir = datafile + '.demoblobs'
		_mk_blobdir( demoblobDir )
		return blobDir, demoblobDir


	dataFileName = 'data.fs'
	clientPipe = env_root.run_file( "zeosocket" )
	dataFile = env_root.data_file( dataFileName )
	blobDir, demoBlobDir = _mk_blobdirs( dataFile )


	sessionDataFile = env_root.data_file( 'sessions.' + dataFileName )
	sessionBlobDir, sessionDemoBlobDir = _mk_blobdirs( sessionDataFile )


	searchDataFile = env_root.data_file( 'search.' + dataFileName )
	searchBlobDir, searchDemoBlobDir = _mk_blobdirs( searchDataFile )

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
				'dataFile': dataFile, 'logfile': env_root.log_file( 'zeo.log' ),
				'sessionDataFile': sessionDataFile, 'sessionBlobDir': sessionBlobDir,
				'searchDataFile': searchDataFile, 'searchBlobDir': searchBlobDir
				}

	# NOTE: DemoStorage is NOT a ConflictResolvingStorage.
	# It will not run our _p_resolveConflict methods.
	demo_conf = configuration
	for i in range(1,4):
		demo_conf = demo_conf.replace( '<filestorage %s>' % i,
									   '<demostorage %s>\n\t\t\t<filestorage %s>' % (i,i) )
	demo_conf = demo_conf.replace( '</filestorage>', '</filestorage>\n\t\t</demostorage>' )
	# Must use non-shared blobs, DemoStorage is missing fshelper.

	env_root.write_conf_file( 'zeo_conf.xml', configuration )
	env_root.write_conf_file( 'demo_zeo_conf.xml', demo_conf )


	base_uri = 'zeo://%(addr)s?storage=%(storage)s&database_name=%(name)s&blob_dir=%(blob_dir)s&shared_blob_dir=%(shared)s'
	file_uri = 'file://%s?database_name=%s&blobstorage_dir=%s'

	uris = []
	demo_uris = []
	file_uris = []
	for storage, name, data_file, blob_dir, demo_blob_dir in ((1, 'Users',    dataFile, blobDir, demoBlobDir),
															  (2, 'Sessions', sessionDataFile, sessionBlobDir, sessionDemoBlobDir),
															  (3, 'Search',   searchDataFile, searchBlobDir, searchDemoBlobDir)):
		uri = base_uri % {'addr': clientPipe, 'storage': storage, 'name': name, 'blob_dir': blob_dir, 'shared': True }
		uris.append( uri )

		uri = base_uri % {'addr': clientPipe, 'storage': storage, 'name': name, 'blob_dir': demo_blob_dir, 'shared': False }
		demo_uris.append( uri )

		file_uris.append( file_uri % (data_file, name, blob_dir) )


	uri_conf = '[ZODB]\nuris = ' + ' '.join( uris )
	demo_uri_conf = '[ZODB]\nuris = ' + ' '.join( demo_uris )

	env_root.write_conf_file( 'zeo_uris.ini', uri_conf )
	env_root.write_conf_file( 'demo_zeo_uris.ini', demo_uri_conf )

	# We assume that runzeo is on the path (virtualenv)
	program = _Program( 'zeo', 'runzeo -C ' + env_root.conf_file( 'zeo_conf.xml' ) )
	program.priority = 0
	env_root.add_program( program )


	return file_uris


from repoze.zodbconn.uri import db_from_uri
from zope.configuration import xmlconfig
from zope import component
from ZODB.DB import ContextManager as DBContext
import ZODB.interfaces

from nti.dataserver import interfaces as nti_interfaces

def _configure_database( env, uris ):

	db = db_from_uri( uris )
	# TODO: Circular import
	import nti.dataserver.utils.example_database_initializer
	component.provideSubscriptionAdapter(
		nti.dataserver.utils.example_database_initializer.ExampleDatabaseInitializer,
		adapts=(ZODB.interfaces.IDatabase,),
		provides=nti_interfaces.IDatabaseInitializer )
	# TODO: Replace this with zope.generations IInstallableSchemaManager
	subscribers = component.subscribers( (db,), nti_interfaces.IDatabaseInitializer )
	with db.transaction( ) as conn:
		for subscriber in subscribers:
			subscriber.init_database( conn )

def temp_get_config( root, demo=False ):
	env = _Env( root, create=False )

	pfx = 'demo_' if demo else ''

	env.zeo_conf = env.conf_file( pfx + 'zeo_conf.xml' )
	env.zeo_client_conf = env.conf_file( pfx + 'zeo_uris.ini' )
	env.zeo_launched = True
	ini = SafeConfigParser()
	ini.read( env.zeo_client_conf )

	def connect_databases(  ):
		import _daemonutils as daemonutils
		import ZEO
		if not getattr( env, 'zeo_launched', False ):
			daemonutils.launch_python_daemon( os.path.join( env.env_root, 'var', 'zeosocket' ),
											  os.path.dirname(ZEO.__file__)  + '/runzeo.py',
											  ['-C', env.zeo_conf],
											  daemon=False )
			env.zeo_launched = True
		if not hasattr( env, 'zeo_uris' ):
			env.zeo_uris = ini.get( 'ZODB', 'uris' )
		if hasattr( env, 'zeo_make_db' ):
			db = env.zeo_make_db()
		else:
			db = db_from_uri( env.zeo_uris )
		return (db.databases['Users'], db.databases['Sessions'], db.databases['Search'])
	env.connect_databases = connect_databases

	return env

def write_configs(root_dir, pserve_ini):
	env = _Env( root_dir, create=True )
	xmlconfig.file( 'configure.zcml', package=sys.modules['nti.dataserver'] )
	uris = _configure_zeo( env )
	_configure_database( env, uris )
	_configure_pubsub_changes( env )
	_configure_pubsub_session( env )

	listener = _Program( 'nti_sharing_listener' )
	listener.priority = 50
	env.add_program( listener )

	listener = _Program( 'nti_index_listener' )
	listener.priority = 50
	env.add_program( listener )

	env.write_supervisor_conf_file( pserve_ini )
	env.write_main_conf()

	return env

def main():
	args = sys.argv

	if len( args ) < 3:
		print( 'Usage: root_dir pserve_ini_file' )
		sys.exit( 1 )

	root_dir = args[1]
	pserve_ini = args[2]
	pserve_ini = os.path.abspath( os.path.expanduser( pserve_ini ) )
	if not os.path.exists( pserve_ini ):
		raise OSError( "No ini file " + pserve_ini )

	write_configs(root_dir, pserve_ini)

if __name__ == '__main__':
	main()
