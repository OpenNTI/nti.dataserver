#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import transaction
import pyramid_zodbconn
import pyramid.security

from zope.component.hooks import setSite, getSite, setHooks


def _early_request_teardown(request):
	"""
	Clean up all the things set up by our new request handler and the
	tweens. Call this function if the request thread will not be returning,
	but these resources should be cleaned up.
	"""

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
		# here. Have seen it at startup (also with some of the new test machinery). Force it back to none (?)
		# It is very bad to raise an exception here, it interacts
		# badly with logging
		try:
			assert old_site is None or old_site is site, "Should not have a site already in place"
		except AssertionError:
			logger.debug( "Should not have a site already in place: %s", old_site, exc_info=True )
			old_site = None

		setSite( site )
		try:
			# NOTE: We have dropped support for pyramid_tm due to breaking changes in 0.7
			# and instead require our own .tweens.transaction_tween
			# Now (and only now, that the site is setup since that's when we can access the DB
			# and get the user) record info in the transaction
			uid = pyramid.security.authenticated_userid( request )
			if uid:
				transaction.get().setUser( uid )
			transaction.get().note( request.url )

			request.environ['nti.early_request_teardown'] = _early_request_teardown

			return self.handler(request)
		finally:
			setSite()


def site_tween_factory(handler, registry):
	"""
	Within the scope of a transaction, gets a connection and installs our
	site manager. Records the active user and URL in the transaction.

	"""
	# Our site setup
	# If we wanted to, we could be setting sites up as we traverse as well;
	# traverse hooks are installed to do this
	setHooks()


	return site_tween( handler )
