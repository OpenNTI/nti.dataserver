#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import time
import pyramid_tm
import transaction
import pyramid_zodbconn
import pyramid.security

from zope.component.hooks import setSite, getSite, setHooks

import ZODB.POSException

def early_request_teardown(request):
	"""
	Clean up all the things set up by our new request handler and the
	tweens. Call this function if the request thread will not be returning,
	but these resources should be cleaned up.
	"""
	# public for testing, mocking

	transaction.commit()
	pyramid_zodbconn.get_connection(request).close()
	setSite( None )
	# Remove the close action that pyramid_zodbconn wants to do.
	# The connection might have been reused by then.
	for callback in request.finished_callbacks:
		if getattr( callback, '__module__', None ) == pyramid_zodbconn.__name__:
			request.finished_callbacks.remove( callback )
			break

class site_tween(object):
	"""
	Within the scope of a transaction, gets a connection and installs our
	site manager. Records the active user and URL in the transaction.

	Public for testing, mocking
	"""

	__slots__ = ('handler',)

	def __init__( self, handler ):
		self.handler = handler

	def __call__( self, request ):

		# Given that we are now using our own traversal module, which
		# honors the zope traversal hooks that install a site as you travers,
		# this is probably not necessary anymore as such.
		conn = pyramid_zodbconn.get_connection( request )
		conn.sync()
		site = conn.root()['nti.dataserver']
		old_site = getSite()
		# Not sure what circumstances lead to already having a site
		# here. Have seen it at startup. Force it back to none (?)
		# It is very bad to raise an exception here, it interacts
		# badly with logging
		try:
			assert old_site is None, "Should not have a site already in place"
		except AssertionError:
			logger.exception( "Should not have a site already in place: %s", old_site )
			old_site = None

		setSite( site )
		try:
			# Now (and only now, that the site is setup since that's when we can access the DB
			# and get the user) record info in the transaction
			uid = pyramid.security.authenticated_userid( request )
			if uid:
				transaction.get().setUser( uid )
			transaction.get().note( request.url )
			request.environ['nti.early_request_teardown'] = early_request_teardown

			response = self.handler(request)
			### FIXME:
			# pyramid_tm <= 0.5 has a bug in that if committing raises a retryable exception,
			# it doesn't actually retry (because commit is inside the __exit__ of a context
			# manager, and when a context manager is exiting normally (not due to an exception),
			# it ignores the return value of __exit__, so the loop
			# doesn't actually loop (i.e., all you can do is raise the exception, you cannot return a value in that scenario,
			# the context manager machinery will ignore it): the normal return statement trumps).
			# Thus, we commit here so that an exception is raised and caught.
			# See https://github.com/Pylons/pyramid_tm/issues/4
			# Confirmed and filed against 0.4. Probably still the case with 0.5, but our tests
			# pass with or without these next two lines. There's no real harm leaving them in, other than
			# that transaction.commit shows up as being called twice in profiles
			if request.method == 'GET' and 'socket.io' not in request.url:
				# GET requests must NEVER have side effects. (Unfortunately, socket.io polling does)
				# So these transactions can safely be aborted and ignored, reducing contention on commit locks
				# TODO: It would be cool to open them readonly.
				# TODO: I don't really know if this is kosher.
				now = time.time()
				transaction.abort()
				done = time.time() # TODO: replace all this with statsd
				logger.debug( "Aborted side-effect free transaction for %s in %ss", request.url, done - now )
			elif not transaction.isDoomed() and not pyramid_tm.default_commit_veto( request, response ):
				exc_info = sys.exc_info()
				try:
					now = time.time()
					transaction.commit()
					done = time.time() # TODO: replace all this with statsd
					logger.debug( "Committed transaction for %s in %ss", request.url, done - now )
					if (done - now) > 10.0:
						# We held locks for a really, really, long time. Why?
						logger.warn( "Slow running commit for %s in %ss", request.url, done - now )
				except AssertionError:
					# We've seen this when we are recalled during retry handling. The higher level
					# is in the process of throwing a different exception and the transaction is
					# already toast, so this commit would never work, but we haven't lost anything;
					# The sad part is that this assertion error overrides the stack trace for what's currently
					# in progress
					logger.exception( "Failing to commit; should already be an exception in progress" )
					if exc_info and exc_info[0]:
						raise exc_info[0], None, exc_info[2]
					else:
						raise
				except ZODB.POSException.StorageError as e:
					if str(e) == 'Unable to acquire commit lock':
						# Relstorage locks. Who's holding it? What's this worker doing?
						# if the problem is some other worker this doesn't help much.
						# Of course by definition, we won't catch it in the act if we're running.
						from ._util import dump_stacks
						body = '\n'.join(dump_stacks())
						print( body, file=sys.stderr )
					raise

			return response
		finally:
			setSite()

def site_tween_factory(handler, registry):
	"""
	Within the scope of a transaction, gets a connection and installs our
	site manager. Records the active user and URL in the transaction.
	Also commits the transaction to work better with :mod:`pyramid_tm`. See
	comments in this package for details.

	"""
	# Our site setup
	# If we wanted to, we could be setting sites up as we traverse as well
	setHooks()


	return site_tween( handler )
