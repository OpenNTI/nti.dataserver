#!/usr/bin/env python2.7
#  Phusion Passenger - http://www.modrails.com/
#  Copyright (c) 2008, 2009 Phusion
#
#  "Phusion Passenger" is a trademark of Hongli Lai & Ninh Bui.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

# Modified by NTI based on dreamhost version as of 2011-09-01 to be compatible
# with gevent

import os, random, sys, struct, select, imp
import exceptions, traceback
import signal

import greenlet
from gevent import core
from gevent.event import Event
import gevent.socket
socket = gevent.socket
from socket import _fileobject
from gevent.socket import EWOULDBLOCK
import logging
logger = logging.getLogger( 'nti.passenger' )

class RequestHandler(object):

	def __init__(self, socket_file, server, owner_pipe, app):
		self.socket_file = socket_file # string path
		self.server = server # socket object
		self.owner_pipe = owner_pipe # FD number
		self.app = app

		self.started = False
		self._accept_server_event = None
		self._accept_owner_event = None
		self._stopped_event = Event()
		self._client_jobs = []


	####### NTI Additions ###########

	def _do_client( self, client, client_addr ):
		close_client = True
		try:
			try:
				env, input_stream = self.parse_request(client)
				if env:
					if env['REQUEST_METHOD'] == 'ping':
						self.process_ping(env, input_stream, client)
					else:
						# Processing the request will expose a 'file-like' object
						# at wsgi.input_stream. We also expose the
						# raw socket (for the sake of web sockets) at 'nti.input_socket'
						env['nti.input_socket'] = input_stream
						env['nti.client_address'] = client_addr
						self.process_request(env, input_stream, client)
						close_client = not env.get( 'nti.keep_alive', False )
				else:
					self.stop()
			except KeyboardInterrupt:
				logger.exception( "Stopping on keyboard interrupt." )
				self.stop()
			except:
				logger.exception( "Failed to handle client" )
		finally:
			try:
				self._client_jobs.remove( greenlet.getcurrent() )
			except: pass
			if close_client:
				try:
					client.close()
				except:
					pass

	def _do_accept_server( self, event, _evtype ):
		# Yay, new client request!
		try:
			client_socket, address = self.server.accept()
		except socket.error, err:
			if err[0] == EWOULDBLOCK:
				return
			raise

		client_socket = gevent.socket.socket(_sock=client_socket)
		# We must keep these alive or they may get
		# GC'd and not finish.
		client_job = gevent.spawn( self._do_client, client_socket, address )
		self._client_jobs.append( client_job )

	def _do_accept_owner( self, event, _evtype ):
		# Something from the owner. Apparently we're supposed to die now.
		self.stop()

	def start_accepting( self ):
		self._accept_server_event = core.read_event(self.server.fileno(), self._do_accept_server, persist=True)
		self._accept_owner_event = core.read_event( self.owner_pipe, self._do_accept_owner, persist=True)

	def stop_accepting(self):
		for evt in (self._accept_server_event, self._accept_owner_event):
			if evt is not None:
				evt.cancel()
		self._accept_owner_event = self._accept_server_event = None


	def start(self):
		"""Start accepting the connections. """
		assert not self.started, '%s already started' % self.__class__.__name__
		self.started = True
		try:
			self.start_accepting()
		except:
			self.kill()
			raise

	def kill(self):
		"""Close the listener socket and stop accepting."""
		self.started = False
		try:
			self.stop_accepting()
		finally:
			try:
				self.cleanup()
			except Exception:
				pass

	def stop(self):
		"""Stop accepting the connections and close the listening socket."""
		self.kill()
		self.post_stop()

	def post_stop(self):
		self._stopped_event.set()

	def serve_forever(self):
		"""Start the server if it hasn't been already started and wait until it's stopped."""
		# add test that serve_forever exists on stop()
		if not self.started:
			self.start()
		try:
			self._stopped_event.wait()
			return True
		except:
			self.stop()
			raise

	main_loop = serve_forever

	######## End NTI Additions #########

	def cleanup(self):
		self.server.close()
		try:
			os.remove(self.socket_file)
		except:
			pass

	def parse_request(self, client):
		buf = ''
		while len(buf) < 4:
			tmp = client.recv(4 - len(buf))
			if len(tmp) == 0:
				return (None, None)
			buf += tmp
		header_size = struct.unpack('>I', buf)[0]

		buf = ''
		while len(buf) < header_size:
			tmp = client.recv(header_size - len(buf))
			if len(tmp) == 0:
				return (None, None)
			buf += tmp

		headers = buf.split("\0")
		headers.pop() # Remove trailing "\0"
		env = {}
		i = 0
		while i < len(headers):
			env[headers[i]] = headers[i + 1]
			i += 2

		return (env, client)

	def process_request(self, env, input_stream, output_stream):
		# The WSGI speculation says that the input paramter object passed needs to
		# implement a few file-like methods. This is the reason why we "wrap" the socket._socket
		# into the _fileobject to solve this.
		#
		# Otherwise, the POST data won't be correctly retrieved by Django.
		#
		# See: http://www.python.org/dev/peps/pep-0333/#input-and-error-streams
		env['wsgi.input']		 = _fileobject(input_stream,'r',512)
		env['wsgi.errors']		 = sys.stderr
		env['wsgi.version']		 = (1, 0)
		env['wsgi.multithread']	 = False
		env['wsgi.multiprocess'] = True
		env['wsgi.run_once']	 = True
		if env.get('HTTPS','off') in ('on', '1'):
			env['wsgi.url_scheme'] = 'https'
		else:
			env['wsgi.url_scheme'] = 'http'


		# The following environment variables are required by WSCI PEP #333
		# see: http://www.python.org/dev/peps/pep-0333/#environ-variables
		if 'HTTP_CONTENT_LENGTH' in env:
			env['CONTENT_LENGTH'] = env.get('HTTP_CONTENT_LENGTH')


		headers_set = []
		headers_sent = []

		def write(data):
			if not headers_set:
				raise AssertionError("write() before start_response()")
			elif not headers_sent:
				# Before the first output, send the stored headers.
				status, response_headers = headers_sent[:] = headers_set
				output_stream.send('Status: %s\r\n' % status)
				for header in response_headers:
					output_stream.sendall('%s: %s\r\n' % header)
				output_stream.sendall('\r\n')
			output_stream.sendall(data)
		def start_response(status, response_headers, exc_info = None ):
			if exc_info:
				try:
					if headers_sent:
						# Re-raise original exception if headers sent.
						raise exc_info[0], exc_info[1], exc_info[2]
				finally:
					# Avoid dangling circular ref.
					exc_info = None
			elif headers_set:
				raise AssertionError("Headers already set!")

			headers_set[:] = [status, response_headers]
			return write

		result = self.app(env, start_response)
		try:
			for data in result:
				# Don't send headers until body appears.
				if data:
					write(data)
			if not headers_sent:
				# Send headers now if body was empty.
				write('')
		finally:
			if hasattr(result, 'close'):
				result.close()

	def process_ping(self, env, input_stream, output_stream):
		output_stream.send("pong")

def import_error_handler(environ, start_response):
	write = start_response('500 Import Error', [('Content-type', 'text/plain')])
	write("An error occurred importing your passenger_wsgi.py")
	raise KeyboardInterrupt # oh WEIRD.

if __name__ == "__main__":
	socket_file = sys.argv[1]
	server = socket.fromfd(int(sys.argv[2]), socket.AF_UNIX, socket.SOCK_STREAM)
	owner_pipe = int(sys.argv[3])

	def sighandler( signum, frame ):
		logger.critical( "Exiting on signal %s %s", signum, frame )
		sys.exit( 42 )

	for sig in (signal.SIGABRT, signal.SIGBUS, signal.SIGFPE, signal.SIGINT, signal.SIGSEGV,
				signal.SIGTERM, signal.SIGHUP):
		gevent.signal( sig, sighandler )

	try:
		app_module = imp.load_source('passenger_wsgi', 'passenger_wsgi.py')
		handler = RequestHandler(socket_file, server, owner_pipe, app_module.application)
	except:
		handler = RequestHandler(socket_file, server, owner_pipe, import_error_handler)

	try:
		job = gevent.spawn( handler.main_loop )
		result = job.get()
		logger.debug( "Completed main loop with %s", result )
	except:
		logger.exception( "Main loop failed with exception" )
	finally:
		handler.cleanup()
