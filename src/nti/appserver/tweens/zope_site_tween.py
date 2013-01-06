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

.. * It has a property called ``possible_site_names``, which is an iterable of the site names
..  to consider. These site names may be found as c

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import transaction
import pyramid_zodbconn
import pyramid.security

from zope import interface
from zope import component

from zope.component import interfaces as comp_interfaces

from zope.component.hooks import setSite, getSite, setHooks, clearSite
from zope.component.persistentregistry import PersistentComponents as _ZPersistentComponents

from zope.site.site import LocalSiteManager as _ZLocalSiteManager
from zope.container.contained import Contained as _ZContained


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

	if 'origin' in request.headers:
		# TODO: The port splitting breaks on IPv6
		# Origin comes in as a complete URL, host and potentially port
		# Sometimes it comes in blank (unit tests, mostly, that don't use proper HTTP libraries)
		# so the below is robust against that, as well as deliberately malformed input
		origin = request.headers['origin']
		__traceback_info__ = origin
		if origin and '//' in origin and ':' in origin:
			host = origin.split( '//' )[1].split( ":" )[0]
			result.append( host.lower() )
	if request.host:
		# Host is a plain name/IP address, and potentially port
		result.append( request.host.split(':')[0].lower() )

	for blacklisted in ('localhost', '0.0.0.0'):
		if blacklisted in result:
			result.remove( blacklisted )

	return result

def _find_site_components(request):
	site_names = _get_possible_site_names( request )
	for site_name in site_names:
		if not site_name:
			return None

		components = component.queryUtility( comp_interfaces.IComponents, name=site_name )

		if components is not None:
			return components

# TODO: All this site mucking may be expensive. It has significant possibilities
# for optimization (caching) using the fact that much of it is read only.

class _BasedSiteManager(_ZLocalSiteManager):
	"""
	A site manager that exists simply to have bases, but not to
	record itself as children of those bases (since that's unnecessary
	for our purposes and leads to conflicts.
	"""

	def _setBases( self, bases ):
		# Bypass the direct superclass.
		_ZPersistentComponents._setBases( self, bases )

	def __init__( self, site, name, bases ):
		# Bypass the direct superclass to avoid setting
		# bases multiple times: NOTE: This means we are fairly tightly coupled
		_ZPersistentComponents.__init__(self)

		# Locate the site manager
		self.__parent__ = site
		self.__name__ = name

		self.__bases__ = bases

	def _newContainerData(self):
		return None # We won't be used as a folder

@interface.implementer(comp_interfaces.ISite)
class _TrivialSite(_ZContained):

	def __init__( self, site_manager ):
		self._sm = site_manager

	def getSiteManager(self):
		return self._sm

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

	Public for testing, mocking.

	The alternative to using a class is using a closure that captures the handler,
	but that's not mockable.
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
		self._debug_site( site )
		site = get_site_for_request( request, site )

		setSite( site )
		try:
			self._configure_transaction( request )
			self._add_properties_to_request( request )

			return self.handler(request)
		finally:
			clearSite()

	def _add_properties_to_request(self, request):
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
		# TODO: Expose the possible_site_names?
		request.environ['nti.early_request_teardown'] = _early_request_teardown

	def _configure_transaction( self, request ):
		# NOTE: We have dropped support for pyramid_tm due to breaking changes in 0.7
		# and instead require our own .tweens.transaction_tween
		# Now (and only now, that the site is setup since that's when we can access the DB
		# and get the user) record info in the transaction
		uid = pyramid.security.authenticated_userid( request )
		if uid:
			transaction.get().setUser( uid )
		transaction.get().note( request.url )


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

def get_site_for_request( request, site=None ):
	"""
	Public for testing purposes only.
	"""
	if site is None:
		site = getSite()

	#assert site.getSiteManager().__bases__ == (component.getGlobalSiteManager(),)
	# Can we find a named site to use?
	site_components = _find_site_components( request )
	if site_components:
		# Yes we can. The site components are only a partial configuration
		# and are not persistent, so we need to use two bases
		# to make it work (order matters). They are also not traversable.
		#assert site_components.__bases__ == (component.getGlobalSiteManager(),)
		#gsm = site_components.__bases__[0]
		#assert site_components.adapters.__bases__ == (gsm.adapters,)

		main_site = site
		site_manager = _BasedSiteManager( main_site, site_components.__name__, (site_components, main_site.getSiteManager(),) )
		site = _TrivialSite( site_manager )
		site.__parent__ = main_site
		site.__name__ = site_components.__name__

	return site

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
