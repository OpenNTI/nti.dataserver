#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import os
import sys
import stat
import tempfile

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
	priority = 999

	def __init__( self, cmd_line ):
		self.cmd_line = cmd_line


class _Env(object):
	env_root = '/'
	settings = {}
	programs = ()

	def __init__( self, root='/', settings=None, create=False ):
		self.env_root = os.path.expanduser( root )
		self.settings = settings or dict(os.environ)
		self.programs = []
		if create:
			os.makedirs( self.env_root )
			os.makedirs( self.run_dir() )
			os.makedirs( os.path.join( self.run_dir() , 'log' ) )

	def add_program( self, program ):
		self.programs.append( program )

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

	def write_conf_file( self, name, contents ):
		write_configuration_file( self.conf_file( name ), contents )


def _configure_zeo( env_root ):
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
	uris = []
	demo_uris = []
	for storage, name, blob_dir, demo_blob_dir in ((1, 'Users',    blobDir, demoBlobDir),
												   (2, 'Sessions', sessionBlobDir, sessionDemoBlobDir),
												   (3, 'Search',   searchBlobDir, searchDemoBlobDir)):
		uri = base_uri % {'addr': clientPipe, 'storage': storage, 'name': name, 'blob_dir': blob_dir, 'shared': True }
		uris.append( uri )

		uri = base_uri % {'addr': clientPipe, 'storage': storage, 'name': name, 'blob_dir': demo_blob_dir, 'shared': False }
		demo_uris.append( uri )


	uri_conf = '[ZODB]\nuris = ' + ' '.join( uris )
	demo_uri_conf = '[ZODB]\nuris = ' + ' '.join( demo_uris )

	env_root.write_conf_file( 'zeo_uris.ini', uri_conf )
	env_root.write_conf_file( 'demo_zeo_uris.ini', demo_uri_conf )


	# We assume that runzeo is on the path (virtualenv)
#	program = _Program()

from ConfigParser import SafeConfigParser
from repoze.zodbconn.uri import db_from_uri

def temp_get_config( root, demo=False ):
	env = _Env( root, create=False )

	pfx = 'demo_' if demo else ''

	env.zeo_conf = env.conf_file( pfx + 'zeo_conf.xml' )
	env.zeo_client_conf = env.conf_file( pfx + 'zeo_uris.ini' )
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

def main():
	root_dir = sys.argv[1]
	env = _Env( root_dir )
	_configure_zeo( env )

if __name__ == '__main__':
	main()
