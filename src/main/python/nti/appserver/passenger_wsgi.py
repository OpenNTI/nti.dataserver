#!/usr/bin/env python2.5

# Notice that the first part of this code MUST be compatible with python2.5
import sys, os
import ConfigParser
my_dir = os.path.abspath( os.path.split( __file__ )[0] )
config = ConfigParser.SafeConfigParser(
	{
		# defaults
		'python': '/opt/local/Library/Frameworks/Python.framework/Versions/2.7/Resources/Python.app/Contents/MacOS/Python',
		'app.root': os.path.expanduser( "~/Projects/DataserverPassenger/public" ),
		'dataserver.dir': os.path.expanduser( '~/Projects/DataserverPassenger/database' ),
		'dataserver.file': 'data.fs'
	})
config.read( os.path.join( os.path.split(__file__)[0], 'dataserver.ini' ) )
for section in ('passenger', 'database'):
	if not config.has_section( section ): config.add_section( section )
INTERP = config.get( 'passenger', 'python' )
if sys.version_info[0] >= 2 and sys.version_info[1] >= 7 and False:
	# If we're already running in a 2.7+ interp, keep it
	INTERP = sys.executable


#Note we don't have the right certs to be prod.
#os.environ['APNS_PROD'] = '1'
os.environ['DATASERVER_DIR'] = config.get( 'database', 'dataserver.dir' )
os.environ['DATASERVER_FILE'] = config.get( 'database', 'dataserver.file' )
# PID file location
os.environ['INSTANCE_HOME'] = os.environ['DATASERVER_DIR']
try:
	os.mkdir( os.path.join( os.environ['INSTANCE_HOME'], 'var' ) )
except: pass
os.environ['DATASERVER_NO_AUTOCREATE_USERS'] = '1'
os.environ['APP_ROOT'] = config.get( 'passenger', 'app.root' )
if config.has_option( 'passenger', 'ld_library_path' ):
	os.environ['LD_LIBRARY_PATH'] = config.get( 'passenger', 'ld_library_path' )
# Switch us to the good python interpreter. Also change out the passenger
# code to one that runs with greenlets.
req_handler = os.path.join( my_dir, 'passenger_request_handler.py' )
if sys.executable != INTERP or req_handler not in sys.argv:
	args = list(sys.argv)
	args[0] = req_handler
	args.insert( 0, INTERP )
	sys.stdout.flush()
	os.execv( INTERP, args )

#####
## From this point on, we can be python2.7
#####

# redirect output to a log file
if 'DATASERVER_NO_REDIRECT' not in os.environ:
	sys.stdout.close()
	sys.stdout = open( os.environ['DATASERVER_DIR'] + '/accesslog.txt', 'a', 1 )
	sys.stderr.close()
	sys.stderr = open( os.environ['DATASERVER_DIR'] + '/errorlog.txt', 'a', 0 )

sys.path.insert( 0, my_dir )
sys.path.insert( 0, os.path.join( my_dir, 'python' ) )
# TODO: configure logging
import logging
logging.basicConfig( level=logging.INFO )
logger = logging.getLogger( 'nti.passenger' )

from hashlib import md5
import traceback

class HandShakeError(ValueError):
	""" Hand shake challenge can't be parsed """
	pass
try:
	import gevent
	import socketio

	import nti.dataserver as dataserver

	def _wsgi_handle_one_response(self):
		result = self.application( self.environ, self.start_response )
		if result:
			self.passenger_response_bodies.extend( result )

	gevent.pywsgi.WSGIHandler.handle_one_response = _wsgi_handle_one_response

	def _wsgi_log_request(self):
		pass
	gevent.pywsgi.WSGIHandler.log_request = _wsgi_log_request

	def _transport_write(self, data=""):
		self.handler.write( data )
	socketio.transports.BaseTransport.write = _transport_write

	class _SocketIOApp( object ):

		def __init__( self, the_app ):
			self.application = the_app
			self.server = AppServer(
					('',8080), self.application,
					policy_server=False,
					namespace=SOCKET_IO_PATH,
					session_manager=dataserver.Dataserver.get_shared_dataserver().session_manager )

		def __call__( self, environ, start_response ):
			try:
				handler = dataserver.socketio_server.SocketIOHandler( environ['nti.input_socket'],
																	  environ['nti.client_address'],
																	  self.server,
																	  rfile=environ['wsgi.input'],
																	  sessions=self.server,
																	  context_manager_callable=dataserver.Dataserver.get_shared_dataserver().dbTrans)
				environ['socketio'] = socketio.protocol.SocketIOProtocol(handler)
				handler.environ = environ
				handler.wsgi_input = environ['wsgi.input']
				handler.application = self.application

				passenger_status = ['200']
				passenger_headers = []
				def h_start_response( status, headers, exc_info=None ):
					passenger_status[0] = status
					passenger_headers.extend( headers )
				def h_reset_passenger():
					passenger_status[0] = 200
					del passenger_headers[:]


				handler.start_response = h_start_response
				handler.reset_passenger = h_reset_passenger
				del handler.handler_types['websocket']
				passenger_response_bodies = []
				handler.passenger_response_bodies = passenger_response_bodies
				def write( data ):
					passenger_response_bodies.append( data )
				handler.write = write
				handler.handle_one_response()
				start_response( passenger_status[0], passenger_headers )
				return passenger_response_bodies
			except:
				# TODO: Almost nothing should actually be getting here. What is?
				logger.exception( "Failed to handle request" )
				start_response( '500 Internal Server Error', [('Content-Type', 'text/plain')], sys.exc_info() )
				return 'Failed to handle request'


	# TODO: Make this dynamic.
	from nti.appserver.application import createApplication, AppServer, SOCKET_IO_PATH
	from nti.dataserver.library import Library
 	root = '/Library/WebServer/Documents/'
 	if "--root" in sys.argv:
 		root = sys.argv[sys.argv.index( "--root" ) + 1]
 	elif 'APP_ROOT' in os.environ:
 		root = os.environ['APP_ROOT']
 	application,main = createApplication( 80,
										  Library( ((root + '/prealgebra', False, 'Prealgebra',
 													 '/prealgebra/icons/chapters/PreAlgebra-cov-icon.png'),
 													(root + '/mathcounts', False, 'MathCounts',
 													 '/mathcounts/icons/mathcounts-logo.gif')) ) )

	application = _SocketIOApp( application )

except ImportError, e:
	traceback.print_exc()
	def application( env, s ):
		s( '500 Error', [('Content-type', 'text/plain'),])
		return [e.message]
except BaseException, e:
	traceback.print_exc()
	def application( env, s ):
		s( '500 Error', [('Content-type', 'text/plain'),])
		return [e.message]


