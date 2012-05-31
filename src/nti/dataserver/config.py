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

from nti.zodb.zlibstorage import install_zlib_client_resolver


def _file_contents_equal( path, contents ):
	""" :return: Whether the file at `path` exists and has `contents` """
	result = False
	if os.path.exists( path ):
		with open( path, 'rU', 1 ) as f:
			path_contents = f.read()
			result = path_contents.strip() == contents.strip()

	return result

def write_configuration_file( path, contents, overwrite=True ):
	""" Ensures the contents of `path` contain `contents`.
	:param bool overwrite: If true (the default), existing files will be replaced. Othewise, existing
		files will not be modified.
	:return: The path.
	"""
	if not overwrite and os.path.exists( path ):
		return path

	if not _file_contents_equal( path, contents ):
		# Must make the file
		logger.debug( 'Writing config file %s', path )
		try:
			os.mkdir( os.path.dirname( path ) )
		except OSError: pass
		with open( path, 'w' ) as f:
			print( contents, file=f )

	return path

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
		self.env_root = os.path.abspath( os.path.expanduser( root ) )
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

	def __init__( self, root='/', settings=None, create=False, only_new=False ):
		super(_Env,self).__init__( root=root, settings=settings )
		self.only_new = only_new
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
		"""
		:return: The absolute path to the file written.
		"""
		return write_configuration_file( self.conf_file( name ), contents, overwrite=not self.only_new )

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

		# write dev config
		enviroment = ['DATASERVER_DIR=%(here)s/../']

		command = 'pserve'
		ini.add_section( 'program:pserve' )
		ini.set( 'program:pserve', 'command', '%s %s' % (command, pserve_ini) )
		ini.set( 'program:pserve', 'environment', ','.join(enviroment) )
		ini.set( 'supervisord', 'nodaemon', 'true' )
		with open( self.conf_file( 'supervisord_dev.conf' ), 'wb' ) as fp:
			ini.write( fp )

		# write demo config
		enviroment.append('DATASERVER_DEMO=1')
		zeo_p = _create_zeo_program(self, 'demo_zeo_conf.xml')
		ini.set('program:zeo', 'command', zeo_p.cmd_line)
		ini.set('program:pserve', 'environment', ','.join(enviroment) )
		for p in self.programs:
			section = 'program:%s' % p.name
			ini.set(section, 'environment', ','.join(enviroment))
		with open( self.conf_file( 'supervisord_demo.conf' ), 'wb' ) as fp:
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

def _create_zeo_program(env_root, zeo_config='zeo_conf.xml' ):
	program = _Program( 'zeo', 'runzeo -C ' + env_root.conf_file( zeo_config ) )
	program.priority = 0
	return program

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

	configuration_dict = {
		'clientPipe': clientPipe, 'logfile': env_root.log_file( 'zeo.log' ),
		'dataFile': dataFile,'blobDir': blobDir,
		'sessionDataFile': sessionDataFile, 'sessionBlobDir': sessionBlobDir,
		'searchDataFile': searchDataFile, 'searchBlobDir': searchBlobDir
		}

	configuration = """
		<zeo>
		address %(clientPipe)s
		</zeo>
		<filestorage 1>
		path %(dataFile)s
		blob-dir %(blobDir)s
		pack-gc false
		</filestorage>
		<filestorage 2>
		path %(sessionDataFile)s
		blob-dir %(sessionBlobDir)s
		pack-gc false
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
		""" % configuration_dict

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

	# Now write a configuration for use with zc.zodbgc, which runs
	# much faster on raw files
	gc_configuration = """
		<zodb Users>
		<filestorage 1>
		path %(dataFile)s
		blob-dir %(blobDir)s
		pack-gc false
		</filestorage>
		</zodb>
		<zodb Sessions>
		<filestorage 2>
		path %(sessionDataFile)s
		blob-dir %(sessionBlobDir)s
		pack-gc false
		</filestorage>
		</zodb>
		<zodb Search>
		<filestorage 3>
		path %(searchDataFile)s
		blob-dir %(searchBlobDir)s
		</filestorage>
		</zodb>
		""" % configuration_dict
	env_root.write_conf_file( 'gc_conf.xml', gc_configuration )

	# Write one for ZEO access for online GC and diagnosis too
	gc_zeo_configuration = """
		<zodb Users>
		<zeoclient 1>
		storage 1
		server %(clientPipe)s
		blob-dir %(blobDir)s
		shared-blob-dir true
		</zeoclient>
		</zodb>
		<zodb Sessions>
		<zeoclient 2>
		storage 2
		server %(clientPipe)s
		blob-dir %(blobDir)s
		shared-blob-dir true
		</zeoclient>
		</zodb>
		<zodb Search>
		<zeoclient 3>
		storage 3
		server %(clientPipe)s
		blob-dir %(blobDir)s
		shared-blob-dir true
		</zeoclient>
		</zodb>
		""" % configuration_dict
	# TODO: Given this conf, and the possibilitiy of using zconfig:// urls in
	# repoze.zodbconn, maybe we should, on the DRY principal? Thus avoiding rewriting
	# stuff in the URI? The reason we haven't so far is the demo URIs differ by
	# blob dir
	env_root.write_conf_file( 'gc_conf_zeo.xml', gc_zeo_configuration )

	def _relstorage_stanza( name="Users", cacheServers=None,
							blobDir=None,
							addr=None,
							db_name=None, db_username=None, db_passwd=None,
							storage_only=False):
		if db_name is None: db_name = name
		if db_username is None: db_username = db_name
		if db_passwd is None: db_passwd = db_name

		DEFAULT_ADDR = "unix_socket /opt/local/var/run/mysql55/mysqld.sock"
		DEFAULT_CACHE = "localhost:11211"
		if addr is None: addr = DEFAULT_ADDR
		if cacheServers is None: cacheServers = DEFAULT_CACHE

		# Environment overrides
		if addr is DEFAULT_ADDR and 'MYSQL_HOST' in os.environ:
			addr = 'host ' + os.environ['MYSQL_HOST']

		if cacheServers is DEFAULT_CACHE and 'MYSQL_CACHE' in os.environ:
			cacheServers = os.environ['MYSQL_CACHE']

		if db_username is db_name and 'MYSQL_USER' in os.environ:
			db_username = os.environ['MYSQL_USER']

		if db_passwd is db_name and 'MYSQL_PASSWD' in os.environ:
			db_passwd = os.environ['MYSQL_PASSWD']

		# Notice that we specify both a section name (<zodb Name>) and
		# the database-nome. Further explanation below.
		result = """
		<zodb %(name)s>
		pool-size 7
		database-name %(name)s
		<relstorage %(name)s>
				blob-dir %(blobDir)s
				cache-servers %(cacheServers)s
				cache-prefix %(db_name)s
				poll-interval 60
				commit-lock-timeout 6
				keep-history false
				pack-gc false
				<mysql>
				db %(db_name)s
				user %(db_username)s
				passwd %(db_passwd)s
				%(addr)s
				</mysql>
		</relstorage>
		</zodb>
		""" % locals()
		if storage_only:
			result = '\n'.join( result.splitlines()[4:-2] )
		return result

	relstorage_configuration = """
	%%import relstorage
	%%import zc.zlibstorage
	%s
	%s
	%s
	""" % (_relstorage_stanza(blobDir=blobDir),
		   _relstorage_stanza(name="Sessions",blobDir=sessionBlobDir),
		   _relstorage_stanza(name="Search",blobDir=searchBlobDir) )
	relstorage_zconfig_path = env_root.write_conf_file( 'relstorage_conf.xml', relstorage_configuration )

	base_uri = 'zeo://%(addr)s?storage=%(storage)s&database_name=%(name)s&blob_dir=%(blob_dir)s&shared_blob_dir=%(shared)s'
	file_uri = 'file://%s?database_name=%s&blobstorage_dir=%s'
	relstorage_zconfig_uri = 'zconfig://' + relstorage_zconfig_path

	uris = []
	demo_uris = []
	file_uris = []
	relstorage_uris = []
	for storage, name, data_file, blob_dir, demo_blob_dir in ((1, 'Users',    dataFile, blobDir, demoBlobDir),
															  (2, 'Sessions', sessionDataFile, sessionBlobDir, sessionDemoBlobDir),
															  (3, 'Search',   searchDataFile, searchBlobDir, searchDemoBlobDir)):
		uri = base_uri % {'addr': clientPipe, 'storage': storage, 'name': name, 'blob_dir': blob_dir, 'shared': True }
		uris.append( uri )

		uri = base_uri % {'addr': clientPipe, 'storage': storage, 'name': name, 'blob_dir': demo_blob_dir, 'shared': False }
		demo_uris.append( uri )

		file_uris.append( file_uri % (data_file, name, blob_dir) )
		# NOTE: The ZConfig parser unconditionally lower cases the names of sections (e.g., <zodb Users> == <zodb users>)
		# While ZConfig doesn't alter the database-name attribute, repoze.zodbconn.resolvers ignores database-name
		# in favor of the section name. However, the database-name is what's used internally by the DB
		# objects to construct and follow the multi-database references. Not all tools suffer from this problem, though,
		# so section name and database-name have to match. The solution is to lowercase the fragment name in the URI.
		# This works because we then explicitly lookup databases by their complete, case-correct name when
		# we return them in a tuple. (Recall that we cannot change the database names once databases exist without
		# breaking all references, but in the future it would be a good idea to name databases in lower case).
		relstorage_uris.append( relstorage_zconfig_uri + '#' + name.lower() )


		convert_configuration = """
		<filestorage source>
			path %s
		</filestorage>
		%s
		""" % (data_file, _relstorage_stanza(name='destination', db_name=name, blobDir=blob_dir,storage_only=True))
		env_root.write_conf_file( 'zodbconvert_%s.xml' % name, convert_configuration )

		env_root.write_conf_file( 'relstorage_pack_%s.xml' %name, _relstorage_stanza( name=name, blobDir=blob_dir, storage_only=True ) )


	uri_conf = '[ZODB]\nuris = ' + ' '.join( uris )
	demo_uri_conf = '[ZODB]\nuris = ' + ' '.join( demo_uris )
	relstorage_uri_conf = '[ZODB]\nuris = ' + ' '.join( relstorage_uris )

	env_root.write_conf_file( 'zeo_uris.ini', uri_conf )
	env_root.write_conf_file( 'demo_zeo_uris.ini', demo_uri_conf )
	env_root.write_conf_file( 'relstorage_uris.ini', relstorage_uri_conf )


	# We assume that runzeo is on the path (virtualenv)
	program = _create_zeo_program(env_root, 'zeo_conf.xml' )
	env_root.add_program( program )

	return file_uris


from repoze.zodbconn.uri import db_from_uri
from zope.configuration import xmlconfig
from zope import component
from ZODB.DB import ContextManager as DBContext
import ZODB.interfaces

from zope.event import notify
from zope.processlifetime import DatabaseOpenedWithRoot

from nti.dataserver import interfaces as nti_interfaces

def _configure_database( env, uris ):
	install_zlib_client_resolver()
	db = db_from_uri( uris )
	# TODO: Circular import
	import nti.dataserver.utils.example_database_initializer
	component.provideUtility(
		nti.dataserver.utils.example_database_initializer.ExampleDatabaseInitializer(),
		name='nti.dataserver-example' )
	# Now, simply broadcasting the DatabaseOpenedWithRoot option
	# will trigger the installers from zope.generations
	notify( DatabaseOpenedWithRoot( db ) )


def temp_get_config( root, demo=False ):
	env = _Env( root, create=False )
	install_zlib_client_resolver()
	pfx = 'demo_' if demo else ''

	env.zeo_conf = env.conf_file( pfx + 'zeo_conf.xml' )
	env.zeo_client_conf = env.conf_file( pfx + 'zeo_uris.ini' )
	env.zeo_launched = True
	ini = SafeConfigParser()
	ini.read( env.zeo_client_conf )

	def connect_databases(  ):
		env.zeo_launched = True
		if not hasattr( env, 'zeo_uris' ):
			env.zeo_uris = ini.get( 'ZODB', 'uris' )
		if hasattr( env, 'zeo_make_db' ):
			db = env.zeo_make_db()
		else:
			db = db_from_uri( env.zeo_uris )
		# See notes in _configure_zeo about names and cases
		return (db.databases['Users'], db.databases['Sessions'], db.databases['Search'])
	env.connect_databases = connect_databases

	return env

def write_configs(root_dir, pserve_ini, update_existing=False):
	env = _Env( root_dir, create=(not update_existing), only_new=update_existing )
	xmlconfig.file( 'configure.zcml', package=sys.modules['nti.dataserver'] )
	uris = _configure_zeo( env )
	if not update_existing:
		_configure_database( env, uris )
	_configure_pubsub_changes( env )
	_configure_pubsub_session( env )

	listener = _Program( 'nti_sharing_listener' )
	listener.priority = 50
	env.add_program( listener )

	listener = _Program( 'nti_index_listener' )
	listener.priority = 50
	env.add_program( listener )

	if not update_existing:
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

	write_configs(root_dir, pserve_ini, '--update_existing' in args)

if __name__ == '__main__':
	main()
