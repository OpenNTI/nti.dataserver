#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides a tween for integrating Pyramid with the ZCA notion of a site.
This sets up the default (root) site before traversal happens. It also
uses the host name to install applicable configuration, if found.

In theory, traversal can then use listeners to set sub-sites as they
are encountered (see :mod:`~nti.appserver.traversal`), but right now that interferes
with our virtual hosting of multiple, differently configured sites by host name
(since they are not part of the traversal tree).

Request Modifications
=====================

After this tween runs, the request has been modified in the following ways.

* It has a property called ``possible_site_names``, which is an
  iterable of the virtual site names to consider. This is also in the
  WSGI environment as ``nti.possible_site_names``. (See :func:`_get_possible_site_names`)

* It has a method called ``early_request_teardown`` for cleaning up
  resources if the request handler won't actually be returning. This is
  also in the WSGI environment as ``nti.early_request_teardown`` as a function
  of the request. (See :func:`_early_request_teardown`.)

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import transaction
import pyramid_zodbconn
from pyramid_zodbconn import get_connection
from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from zope.component.hooks import setSite, getSite, setHooks, clearSite

def _get_possible_site_names(request):
	"""
	Look for the current request, and return an ordered list
	of site names the request could be considered to be for.
	The list is ordered in preference from most specific to least
	specific. The HTTP origin is considered the most preferred, followed
	by the HTTP Host.

	:return: An ordered sequence of string site names. If there is no request
		or a preferred site cannot be found, returns an empty sequence.
	"""

	result = []

	if b'origin' in request.headers:
		# TODO: The port splitting breaks on IPv6
		# Origin comes in as a complete URL, host and potentially port
		# Sometimes it comes in blank (unit tests, mostly, that don't use proper HTTP libraries)
		# so the below is robust against that, as well as deliberately malformed input
		origin = request.headers[b'origin'].decode('ascii')
		__traceback_info__ = origin
		if origin and '//' in origin and ':' in origin:
			host = origin.split( '//' )[1].split( ":" )[0]
			result.append( host.lower() )
	if request.host:
		# Host is a plain name/IP address, and potentially port
		host = request.host.split(':')[0].lower()
		if host not in result: # no dups
			result.append( host )

	for blacklisted in ('localhost', '0.0.0.0'):
		if blacklisted in result:
			result.remove( blacklisted )

	return result

def _early_request_teardown(request):
	"""
	Clean up all the things set up by our new request handler and the
	tweens. Call this function if the request thread will not be returning,
	but these resources should be cleaned up.
	"""

	transaction.commit()
	request.environ['nti.early_teardown_happened'] = True
	get_connection(request).close()
	setSite( None )
	# Remove the close action that pyramid_zodbconn wants to do.
	# The connection might have been reused by then.
	for callback in request.finished_callbacks:
		if getattr( callback, '__module__', None ) == pyramid_zodbconn.__name__:
			request.finished_callbacks.remove( callback )
			break

# Make zope site managers a bit more compatible with pyramid.
from zope.site.site import LocalSiteManager as _ZLocalSiteManager
from zope.cachedescriptors.property import readproperty
def _notify( self, *events ):
	for _ in self.subscribers( events, None ):
		pass
_ZLocalSiteManager.notify = _notify
_ZLocalSiteManager.has_listeners = True
# make the settings a readable property but still overridable
# on an instance, just in case
_ZLocalSiteManager.settings = readproperty( lambda s: get_current_request().nti_settings )

class site_tween(object):
	"""
	Within the scope of a transaction, gets a connection and installs our
	site manager. Records the active user and URL in the transaction.

	Public for testing, mocking. The alternative to using a class is
	using a closure that captures the handler, but that's not
	mockable.

	.. warning ::
		This only sets the current ZCA site. It *does not*
		set the request's registry, or Pyramid's current registry
		(:func:`pyramid.threadlocal.get_current_registry`). These must be
		left as the global registry. Our sites extend this global registry
		so it would seem that all the settings would be available.
		However, Pyramid configures some things lazily and would thus
		place some configuration in local sites; moreover, this
		configuration is often not-persistent and causes errors committing
		transactions (and we don't want to save it anyway). This is
		specifically seen with renderers and renderer factories. Thus, one
		must be careful using pyramid APIs that touch the current registry if there is a chance
		that site-local configuration should be used. Fortunately, these APIs are rare.

	"""

	__slots__ = ('handler',)

	def __init__( self, handler ):
		self.handler = handler

	def __call__( self, request ):
		conn = get_connection( request )
		#conn.sync() # syncing the conn aborts the transaction.
		site = conn.root()['nti.dataserver']
		self._debug_site( site )
		self._add_properties_to_request( request )

		site = get_site_for_request( request, site )

		setSite( site )
		# See comments in the class doc about why we cannot set the Pyramid request/current site
		try:
			self._configure_transaction( request )

			return self.handler(request)
		finally:
			clearSite()

	def _add_properties_to_request(self, request):
		request.environ['nti.pid'] = os.getpid() # helpful in debug tracebacks
		request.environ['nti.early_request_teardown'] = _early_request_teardown
		request.environ['nti.possible_site_names'] = tuple(_get_possible_site_names( request ) )
		# The "proper" way to add properties is with request.set_property, but
		# this is easier and faster.
		request.early_request_teardown = _early_request_teardown
		request.possible_site_names = request.environ['nti.possible_site_names']
		request.nti_settings = request.registry.settings # shortcut
		# In [15]: %%timeit
		#   ....: r = pyramid.request.Request.blank( '/' )
		#   ....: p(r)
		#   ....:
		# 100000 loops, best of 3: 7.8 us per loop
		#
		# In [16]: %%timeit # set_property uses type() and adds 50us
		#   ....: r = pyramid.request.Request.blank( '/' )
		#   ....: r.set_property( p )
		#   ....: r.p
		#   ....:
		# 10000 loops, best of 3: 57.4 us per loop


	def _configure_transaction( self, request ):
		# NOTE: We have dropped support for pyramid_tm due to breaking changes in 0.7
		# and instead require our own .tweens.transaction_tween
		# Now (and only now, that the site is setup since that's when we can access the DB
		# and get the user) record info in the transaction
		uid = authenticated_userid( request )
		if uid:
			transaction.get().setUser( uid )



	def _debug_site( self, new_site ):
		if __debug__: # pragma: no cover
			old_site = getSite()
			# Not sure what circumstances lead to already having a site
			# here. Have seen it at startup (also with some of the new test machinery). Force it back to none (?)
			# It is very bad to raise an exception here, it interacts
			# badly with logging
			try:
				assert old_site is None or old_site is new_site, "Should not have a site already in place"
			except AssertionError:
				logger.debug( "Should not have a site already in place: %s", old_site, exc_info=True )

from nti.dataserver.site import get_site_for_site_names
def get_site_for_request( request, site=None ):
	"""
	Public for testing purposes only.
	"""
	site_names = getattr( request, 'possible_site_names', None ) or _get_possible_site_names( request )
	return get_site_for_site_names( site_names, site=site )

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
