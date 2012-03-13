import logging
logger = logging.getLogger( __name__ )

import sys
import os
import subprocess
import types
import hashlib

import zdaemon.zdctl

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
			print >> f, contents

def launch_python_daemon( flag_file, path, args, daemon=None, **kwargs ):
	"""
	Launches a python program using the current interpreter. Puts
	this directory on the python path.

	:param string flag_file: A path that the running process will create
		and delete as it launches.
	:param string path: A path to the .py file to run.
	:param sequence args: The arguments to the process, one per element.
	:param bool daemon: If not `None`, a boolean giving whether to spawn
		as a daemon. If `None` or not given, then the default is used,
		which comes from the environment.
	:param dict kwargs: The remainder of the keyword arguments are passed
		to :class:`subprocess.Popen`. Our default is to close file descriptors
		and redirect stdin/out/err to /dev/null (if `daemon` winds up True)
	"""
	redirect = daemon
	if redirect is None:
		redirect = 'DATASERVER_NO_REDIRECT' not in os.environ # daemon by default

	serv_env = dict(os.environ)
	# If we ourself were launched as a daemon, unless
	# we remove this variable, then launching a sub-daemon fails.
	# zdaemon 2.0.4
	serv_env.pop( 'DAEMON_MANAGER_MODE', None )
	# Construct a pythonpath. Notice that we don't use
	# sys.path, that will have had eggs added to it.
	pythonpath = []
	if 'PYTHONPATH' in serv_env:
		pythonpath = serv_env['PYTHONPATH'].split( os.path.pathsep )
		while '' in pythonpath: pythonpath.remove( '' )

	mypath = os.path.split( os.path.dirname( __file__ ) )[0]
	if mypath not in pythonpath: # Ensure we don't keep duplicating as sub-daemons spawn
		pythonpath.insert( 0, mypath )
	mypath = os.path.split( mypath )[0]
	if mypath and mypath != '/' and mypath not in pythonpath:
		pythonpath.insert( 0, mypath )
	serv_env['PYTHONPATH'] = os.path.pathsep.join( pythonpath )

	if path.endswith( '.pyc' ):
		# Sometimes we have compiled files, sometimes not.
		# make sure we always launch the uncompiled version to avoid
		# conflict warnings
		path = path[0:-1]

	path_and_args = ' '.join( ([sys.executable, path] + args) )
	args = [sys.executable, zdaemon.zdctl.__file__]
	config_file = os.path.expanduser( flag_file + '.zconf.xml' )
	flag_file = os.path.expanduser( flag_file )
	args.append( '-C' )
	args.append( config_file )
	args.append('start' )

	configuration = """
		<runner>
		program %(path_and_args)s
		daemon %(daemon)s
		directory %(directory)s
		socket-name %(socket-name)s
		</runner>
		<environment>
		PYTHONPATH %(pythonpath)s""" % { 'path_and_args': path_and_args, 'daemon': str(redirect).lower(),
										 'directory': os.path.dirname( flag_file ), 'socket-name': flag_file + '.zdsock',
										 'pythonpath': serv_env['PYTHONPATH']
										 }

	for k in ('INSTANCE_HOME',
			  'DATASERVER_DIR', 'DATASERVER_FILE', 'DATASERVER_DEMO', 'DATASERVER_SYNC_CHANGES',
			  'LD_LIBRARY_PATH' ):
		if k in serv_env:
			configuration += "\n\t\t%s %s" % ( k, serv_env[k] )

	configuration += """
		</environment>
	"""

	write_configuration_file( config_file, configuration )

	logger.debug( "Launching daemon %s %s", path, args )
	with open( '/dev/null', 'r+' ) as dev_null:
		in_out = dev_null if redirect else None
		popen_args = { 'close_fds': True,
					   'stdin': in_out, 'stdout': in_out, 'stderr': in_out }
		popen_args.update( kwargs )
		popen_args.pop( 'env', None )
		subprocess.Popen( args, env=serv_env, **popen_args )

def launch_python_function_as_daemon( func, args=(), directory='/tmp', qualifier='', daemon=None ):
	"""
	Given a function, derives a daemon control name within the given scope,
	and runs that function as a daemon.
	:param function func: A module-level named function, not a method.
	:param string scope: The filesystem directory to locate the daemon flag file in.
	:param bool daemon: As for :func:`launch_python_daemon`
	"""
	# TODO: Once zope.dottedname is a fixed requirement, we may
	# be able to relax this somewhat? At least we could take callable
	# types
	assert isinstance( func, types.FunctionType )

	flag_name = hashlib.md5( func.__module__ + func.__name__ + qualifier ).hexdigest()
	flag_name = os.path.join( directory, flag_name )

	daemon_args =  ['--func', func.__module__, func.__name__]
	daemon_args.extend( args )
	launch_python_daemon( flag_name, __file__, daemon_args )

_resolve = None

from zope.dottedname.resolve import resolve as _resolve


def load_func( module_name, local_name ):
	return _resolve( module_name + '.' + local_name )

def _run_main(args=None):
	if args is None:
		args = sys.argv[1:]

	if args[0] == '--func':
		# TODO: Configuration.
		# TODO: Logging. Notice this conflicts with
		# application.py
		logging.basicConfig( level=logging.WARN )
		logging.getLogger( 'nti' ).setLevel( logging.DEBUG )
		logging.root.handlers[0].setFormatter( logging.Formatter( '%(asctime)s [%(name)s] %(levelname)s: %(message)s' ) )

		func = load_func( args[1], args[2] )
		func( *args[3:] )
	else:
		raise NotImplementedError()


if __name__ == '__main__':
	_run_main()
