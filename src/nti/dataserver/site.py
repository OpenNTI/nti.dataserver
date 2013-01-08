#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration between the ZCA ``site`` system, configured site
policies, and the Dataserver.

In the Zope world, sites are instances of IComponents. Typically they
are arranged in a tree, with the global site at the root of the tree.
A site is held in a *site manager*. Sites inherit configuration from their
parents (bases, which may or may not be their ``__parent__``). Often, they are
persistent and part of the traversal tree. One site is the current site and
the ZCA functions (e.g., :meth:`.IComponentArchitecture.queryUtility`) apply to
that site.

Our application has one persistent site, the dataserver site,
containing persistent utilities (such as the dataserver); see
:mod:`nti.dataserver.generations.install` This site, or a desndent of
it, must always be the current site when executing application code.

In our application, we also have the concept of site policies,
something that is applied based on virtual hosting. A site policy is
also an ``IComponents``, registered in the global site as a utility named
for the hostname to which it should apply (e.g., ``mathcounts.nextthought.com``).
These are not necessarily persistent and part of the traversal tree.

This there are two things to accomplish: make the dataserver site the current site, and
also construct a site that descends from that site and contains any applicable policies.

.. $Id$
"""

# turn off warning for not calling superclass, calling indirect superclass and accessing protected methods.
# we're deliberately doing both
#pylint: disable=W0233,W0231,W0212

from __future__ import print_function, unicode_literals, absolute_import
logger = __import__( 'logging' ).getLogger( __name__ )


import contextlib

import gevent.queue
import gevent.local

import ZODB.interfaces
import ZODB.POSException

from zope import interface
from zope import component

from zope.component.hooks import site as using_site
from zope.component.hooks import getSite
from zope.component.persistentregistry import PersistentComponents as _ZPersistentComponents

from zope.site.site import LocalSiteManager as _ZLocalSiteManager
from zope.container.contained import Contained as _ZContained


import transaction

from zope.component import interfaces as comp_interfaces
from nti.dataserver import interfaces
from nti.dataserver.interfaces import InappropriateSiteError, SiteNotInstalledError


@contextlib.contextmanager
def _connection_cm():

	ds = component.getUtility( interfaces.IDataserver )
	conn = ds.db.open()
	try:
		yield conn
	finally:
		conn.close()

@contextlib.contextmanager
def _site_cm(conn, site_names=()):
	# If we don't sync, then we can get stale objects that
	# think they belong to a closed connection
	# TODO: Are we doing something in the wrong order? Connection
	# is an ISynchronizer and registers itself with the transaction manager,
	# so we shouldn't have to do this manually
	# ... I think the problem was a bad site. I think this can go away.
	#conn.sync()
	# In fact, it must go away; if we sync the conn, we lose the
	# current transaction
	sitemanc = conn.root()['nti.dataserver']
	# Put into a policy if need be
	sitemanc = get_site_for_site_names( site_names, site=sitemanc )

	with using_site( sitemanc ):
		if component.getSiteManager() != sitemanc.getSiteManager(): # pragma: no cover
			raise SiteNotInstalledError( "Hooks not installed?" )
		if component.getUtility( interfaces.IDataserver ) is None: # pragma: no cover
			raise InappropriateSiteError()
		yield sitemanc



def _find_site_components(site_names):
	"""
	Return an IComponents implementation named for the first virtual site
	found in the sequence of site_names. If no such components can be found,
	returns none.
	"""
	for site_name in site_names:
		if not site_name: # Empty/default. We want the global. This should only ever be at the end
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
		# bases multiple times and initing the BTree portion, which we won't use
		# NOTE: This means we are fairly tightly coupled
		_ZPersistentComponents.__init__(self)

		# Locate the site manager
		self.__parent__ = site
		self.__name__ = name

		self.__bases__ = bases

	def _newContainerData(self): # pragma: no cover
		return None # We won't be used as a folder

@interface.implementer(comp_interfaces.ISite)
class _TrivialSite(_ZContained):

	def __init__( self, site_manager ):
		self._sm = site_manager

	def getSiteManager(self):
		return self._sm

def get_site_for_site_names( site_names, site=None ):
	"""
	Provisional API, public for testing purposes only.

	Return an :class:`ISite` implementation named for the first virtual site
	found in the sequence of site_names. If no such site can be found,
	returns the fallback site.

	:param site_names: Sequence of strings giving the virtual host names
		to use.
	:keyword site: If given, this will be the fallback site manager. If
		not given, then the currently installed site will be used.
	"""


	if site is None:
		site = getSite()

	#assert site.getSiteManager().__bases__ == (component.getGlobalSiteManager(),)
	# Can we find a named site to use?
	site_components = _find_site_components( site_names )
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

def run_job_in_site(func, retries=0, sleep=None, site_names=()):
	"""
	Runs the function given in `func` in a transaction and dataserver local
	site manager. See :class:`.IDataserverTransactionRunner`

	:return: The value returned by the first successful invocation of `func`.
	"""
	note = func.__doc__
	if note:
		note = note.split('\n', 1)[0]
	else:
		note = func.__name__

	with _connection_cm() as conn:
		for i in xrange(retries + 1):

			# Opening the connection registered it with the transaction manager as an ISynchronizer.
			# Ultimately this results in newTransaction being called on the connection object
			# at `transaction.begin` time, which in turn syncs the storage. However,
			# when multi-databases are used, the other connections DO NOT get this called on them
			# if they are implicitly loaded during the course of object traversal or even explicitly
			# loaded by name turing an active transaction. This can lead to extra read conflict errors
			# (particularly with RelStorage which explicitly polls for invalidations at sync time).
			# (Once a multi-db connection has been used, then the next time it would be sync'd. A multi-db
			# connection is associated with the same connection to another database for its lifetime, and
			# when open()'d will sync all other such connections. Corrollary: ALWAYS go through
			# a connection object to get access to multi databases; never go through the database object itself.)

			# As a workaround, we iterate across all the databases and sync them manually; this increases the
			# cost of handling transactions for things that do not use the other connections, but ensures
			# we stay nicely in sync.

			# JAM: 2012-09-03: With the database resharding, evaluating the need for this.
			# Disabling it.
			#for db_name, db in conn.db().databases.items():
			#	__traceback_info__ = i, db_name, db, func
			#	if db is None: # For compatibility with databases we no longer use
			#		continue
			#	c2 = conn.get_connection(db_name)
			#	if c2 is conn:
			#		continue
			#	c2.newTransaction()

			# Now fire 'newTransaction' to the ISynchronizers, including the root connection
			# This may result in some redundant fires to sub-connections.
			t = transaction.begin()
			if i:
				t.note("%s (retry: %s)" % (note, i))
			else:
				t.note(note)
			try:
				with _site_cm(conn, site_names):
					result = func()
					# Commit the transaction while the site is still current
					# so that any before-commit hooks run with that site
					# (Though this has the problem that after-commit hooks would have an invalid
					# site!)
					t.commit()
				# No errors, return the result
				return result
			except transaction.interfaces.TransientError as e:
				t.abort()
				if i == retries:
					# We failed for the last time
					raise
				logger.debug( "Retrying transaction %s on exception (try: %s): %s", func, i, e )
				if sleep is not None:
					gevent.sleep( sleep )
			except transaction.interfaces.DoomedTransaction:
				raise
			except ZODB.POSException.StorageError as e:
				if str(e) == 'Unable to acquire commit lock':
					# Relstorage locks. Who's holding it? What's this worker doing?
					# if the problem is some other worker this doesn't help much
					from nti.appserver._util import dump_stacks
					import sys
					body = '\n'.join(dump_stacks())
					print( body, file=sys.stderr )
				raise
			except:
				t.abort()
				raise

interface.directlyProvides( run_job_in_site, interfaces.IDataserverTransactionRunner )
run_job_in_site.__doc__ = interfaces.IDataserverTransactionRunner['__call__'].getDoc()
