#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration between the ZCA ``site`` system, configured site
policies, and the Dataserver.

In the Zope world, sites are objects that can express configuration by
holding onto an instance of IComponents known as its *site manager*.
Typically they are arranged in a tree, with the global site at the
root of the tree. Site managers inherit configuration from their
parents (bases, which may or may not be their ``__parent__``). Often,
they are persistent and part of the traversal tree. One site is the
current site and the ZCA functions (e.g.,
:meth:`.IComponentArchitecture.queryUtility`) apply to that site.

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

$Id$
"""

# turn off warning for not calling superclass, calling indirect superclass and accessing protected methods.
# we're deliberately doing both
# pylint: disable=W0233,W0231,W0212
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import contextlib
import warnings

from zope import interface
from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import setSite
from zope.component.hooks import site as current_site
from zope.component import interfaces as comp_interfaces
from zope.component.persistentregistry import PersistentComponents as _ZPersistentComponents

from zope.container.contained import Contained as _ZContained
from zope.traversing import interfaces as trv_interfaces

from zope.site.site import LocalSiteManager as _ZLocalSiteManager
from zope.site.interfaces import IRootFolder

from nti.dataserver import interfaces
from nti.dataserver.interfaces import InappropriateSiteError, SiteNotInstalledError

from persistent import Persistent

@contextlib.contextmanager
def _connection_cm():

	ds = component.getUtility( interfaces.IDataserver )
	conn = ds.db.open()
	for c in conn.connections.values():
		c.setDebugInfo("_connection_cm")
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

	with current_site( sitemanc ):
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
	for our purposes and leads to conflicts).
	"""

	# Note that the adapter registries in the base objects /will/ have
	# weak references to this object; it's very hard to stop this. These
	# will stick around until a gc is run. (For testing purposes,
	# it is important to GC or you can get weird errors like:
	# File "zope/interface/adapter.py", line 456, in changed
	#    super(AdapterLookupBase, self).changed(None)
	# File "ZODB/Connection.py", line 857, in setstate
	#    raise ConnectionStateError(msg)
	#  ConfigurationExecutionError: <class 'ZODB.POSException.ConnectionStateError'>: Shouldn't load state for 0x237f4ee301650a49 when the connection is closed
	# in:
	# File "zope/site/configure.zcml", line 13.4-14.71
	# <implements interface="zope.annotation.interfaces.IAttributeAnnotatable" />
	# Fortunately, Python's GC is precise and refcounting, so as long as we do not leak
	# refs to these, we're fine

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

	def __reduce__(self):
		raise TypeError("Should not be pickled")
	def __getstate__(self):
		raise TypeError("Should not be pickled")

class _HostSiteManager(_BasedSiteManager):
	"""
	A site manager that is intended to be used with globally
	registered IComponents plus the dataserver persistent components.
	"""

	def __init__( self, site, name, host_components, persistent_components ):
		self._host_components = host_components
		self._persistent_components = persistent_components
		_BasedSiteManager.__init__( self,
									site,
									name,
									(host_components, persistent_components) )

@interface.implementer(comp_interfaces.ISite)
class _TrivialSite(_ZContained):

	def __init__( self, site_manager ):
		self._sm = site_manager

	def getSiteManager(self):
		return self._sm

	def __reduce__(self):
		raise TypeError("Should not be pickled")

def get_site_for_site_names( site_names, site=None ):
	"""
	Provisional API, public for testing purposes only.

	Return an :class:`ISite` implementation named for the first virtual site
	found in the sequence of site_names. If no such site can be found,
	returns the fallback site.

	:param site_names: Sequence of strings giving the virtual host names
		to use.
	:keyword site: If given, this will be the fallback site (and site manager). If
		not given, then the currently installed site will be used.
	"""

	if site is None:
		site = getSite()

	#assert site.getSiteManager().__bases__ == (component.getGlobalSiteManager(),)
	# Can we find a named site to use?
	site_components = _find_site_components( site_names ) if site_names else None # micro-opt to not call if no names
	if site_components:
		# Yes we can.
		site_name = site_components.__name__
		# Do we have a persistent site installed in the database? If yes,
		# we want to use that.
		try:
			pers_site = site['++etc++hostsites'][site_name]
			site = pers_site
		except (KeyError,TypeError):
			# No, nothing persistent, dummy one up.
			# Note that this code path is deprecated now and not
			# expected to be hit.

			# The site components are only a
			# partial configuration and are not persistent, so we need
			# to use two bases to make it work (order matters) (for
			# example, the main site is almost always the
			# 'nti.dataserver' site, where the persistent intid
			# utilities live; the named sites do not have those and
			# cannot have the persistent nti.dataserver as their real
			# base, so the two must be mixed). They are also not
			# traversable.

			# Host comps used to be simple, but now they may be hierarchacl
			#assert site_components.__bases__ == (component.getGlobalSiteManager(),)
			#gsm = site_components.__bases__[0]
			#assert site_components.adapters.__bases__ == (gsm.adapters,)

			# But the current site, when given, must always be the main
			# dataserver site
			assert isinstance( site, Persistent )
			assert isinstance( site.getSiteManager(), Persistent )

			main_site = site
			site_manager = _HostSiteManager( main_site.__parent__,
											 main_site.__name__,
											 site_components,
											 main_site.getSiteManager() )
			site = _TrivialSite( site_manager )
			site.__parent__ = main_site
			site.__name__ = site_name

	return site

from zope.proxy import non_overridable
from zope.proxy import ProxyBase


class _ProxyTraversedSite(ProxyBase):
	"""
	We need to be able to control the site manager used
	by sites we traverse to in order to ensure that host
	configuration is at the right place in the resolution order.
	But a site can be literally any type of object. So we fake out the
	siteManager methods but proxy everything else.
	"""

	def __new__( cls, base, site_manager ):
		return ProxyBase.__new__( cls, base )

	def __init__( self, base, site_manager ):
		ProxyBase.__init__( self, base )
		self.__site_manager = site_manager

	@non_overridable
	def getSiteManager(self):
		return self.__site_manager

	@non_overridable
	def setSiteManager(self, new_man):
		raise ValueError()

@component.adapter(comp_interfaces.ISite,trv_interfaces.IBeforeTraverseEvent)
def threadSiteSubscriber( new_site, event ):
	"""
	Set the current ``zope.component.hooks`` site to
	the ``new_site`` object found during traversal,
	being careful to maintain any previously installed host (site-name)
	configurations as lower priority than the new site.

	Sites encountered during traversal are expected to have the
	main application site (e.g., ``nti.dataserver``) in their base chain
	so we have access to its configuration and persistent utilities.
	This implies that sites encountered during traversal are either
	synthetic (generated by a traversal adapter to use some particular
	``IComponents``)  or themselves persistent.

	Because of this, when we encounter the root or dataserver folders
	as sites, we take no action.

	We expect that something else takes care of clearing the site.
	"""

	if (interfaces.IDataserverFolder.providedBy( new_site )
		or IRootFolder.providedBy( new_site ) ):
		# TODO: Since we get these events, we could
		# actually replace nti.appserver.tweens.zope_site_tween
		# with this. That's probably the longterm answer.
		return

	# We support exactly three cases:
	# 1. No current site
	# 2. The current site is the site established by get_site_for_site_names
	# 3. The current site is a site previously added by this function.
	# Anything else is forbidden.
	# It turns out that case two and three are exactly the same:
	# we always want to proxy, putting the preserved host components
	# at the end of the new proxy RO.
	current_site = getSite()
	if current_site is None:
		# Nothing to do
		setSite( new_site )
	elif hasattr( current_site.getSiteManager(), '_host_components' ):
		# A site synthesized by get_site_for_site_names
		host_components = current_site.getSiteManager()._host_components
		# We need to keep host_components in the bases
		# for the new site. Where to put it is tricky
		# if we want to support multiple layers of overriding
		# of host registrations. Fortunately, the zope.interface.ro
		# machinery does exactly the right thing if we tack host
		# components (which are probably not already in the list)
		# on to the end. If they are in the list already, they
		# stay where they were.
		new_bases = new_site.getSiteManager().__bases__ + (host_components,)
		# TODO: We don't need to proxy the site manager, right?
		# it's almost never special by itself...
		new_site_manager = _BasedSiteManager( new_site.__parent__,
											  new_site.__name__,
											  new_bases )
		new_site_manager._host_components = host_components
		new_fake_site = _ProxyTraversedSite( new_site,
											 new_site_manager )

		setSite( new_fake_site )
	else:
		raise ValueError("Unknown kind of site", current_site)


from nti.utils.transactions import TransactionLoop
class _RunJobInSite(TransactionLoop):

	def __init__( self, *args, **kwargs ):
		self.site_names = kwargs.pop( 'site_names' )
		self.job_name = kwargs.pop( 'job_name' )
		self.side_effect_free = kwargs.pop('side_effect_free')
		super(_RunJobInSite,self).__init__( *args, **kwargs )

	def describe_transaction( self, *args, **kwargs ):
		if self.job_name:
			return self.job_name
		# Derive from the function
		func = self.handler
		note = func.__doc__
		if note:
			note = note.split('\n', 1)[0]
		else:
			note = func.__name__
		return note

	def run_handler( self, conn,  *args, **kwargs ):
		with _site_cm(conn, self.site_names):
			for c in conn.connections.values():
				c.setDebugInfo(self.site_names)
			result = self.handler( *args, **kwargs )

			# Commit the transaction while the site is still current
			# so that any before-commit hooks run with that site
			# (Though this has the problem that after-commit hooks would have an invalid
			# site!)
			# JAM: DISABLED because the pyramid requests never ran like this:
			# they commit after they are done and the site has been removed
			# t.commit()

			return result

	def __call__( self, *args, **kwargs ):
		with _connection_cm() as conn:
			for c in conn.connections.values():
				c.setDebugInfo(self.describe_transaction(*args, **kwargs))
			# Notice we don't keep conn as an ivar anywhere, to avoid
			# any chance of circular references. These need to be sure to be
			# reclaimed
			return super(_RunJobInSite,self).__call__( conn, *args, **kwargs )

_marker = object()

def run_job_in_site(func,
					retries=0,
					sleep=None,
					site_names=_marker,
					job_name=None,
					side_effect_free=False):
	"""
	Runs the function given in `func` in a transaction and dataserver local
	site manager. See :class:`.IDataserverTransactionRunner`

	:return: The value returned by the first successful invocation of `func`.
	"""

	# site_names is deprecated, we want to start preserving
	# the current site. Because the current site should be based on the
	# current site names FOR NOW, preserving the current site names
	# is equivalent. THIS IS CHANGING though.
	if site_names is not _marker:
		warnings.warn("site_names is deprecated. "
					  "Call this already in the appropriate site",
					  FutureWarning )
	else:
		# This is a bit scuzzy; that's part of why this is going away.
		# Note the nearly-circular import
		from nti.appserver.policies.site_policies import get_possible_site_names
		site_names = get_possible_site_names()

	return _RunJobInSite( func,
						  retries=retries,
						  sleep=sleep,
						  site_names=site_names,
						  job_name=job_name,
						  side_effect_free=side_effect_free)()

interface.directlyProvides( run_job_in_site, interfaces.IDataserverTransactionRunner )
run_job_in_site.__doc__ = interfaces.IDataserverTransactionRunner['__call__'].getDoc()

from zope.site.folder import Folder
from .interfaces import IHostSitesFolder
from .interfaces import IHostPolicyFolder
from .interfaces import IHostPolicySiteManager
from .interfaces import IDataserverFolder

from zope.component.interfaces import IComponents
from zope.traversing.interfaces import IEtcNamespace

@interface.implementer(IHostSitesFolder)
class HostSitesFolder(Folder):
	"""
	Simple container implementation for named host sites.
	"""

@interface.implementer(IHostPolicyFolder)
class HostPolicyFolder(Folder):
	"""
	Simple container implementation for the named host site.
	"""

	def __str__(self):
		return 'HostPolicyFolder(%s)' % self.__name__
	def __repr__(self):
		return 'HostPolicyFolder(%s,%s)' % (self.__name__,id(self))

@interface.implementer(IHostPolicySiteManager)
class HostPolicySiteManager(_ZLocalSiteManager):
	pass


from zope.interface import ro
def synchronize_host_policies():
	"""
	Called within a transaction with a site being the current dataserver
	site, find any :mod:`z3c.baseregistry` components that
	should be sites, and register them in the database.
	"""

	# TODO: We will ultimately need to deal with removing and renaming
	# of these

	# Resolution order: The actual ISite __parent__ order is not
	# important, so we can keep them flat to mirror the GSM IComponents
	# registrations. What matters is the __bases__ of the site managers.
	# Now, if the global IComponents are themselves flat, then it doesn't matter;
	# however, if you have a hierarchy (and we do) then it matters critically, because
	# we need to pick up persistent utilities from these objects, as well as
	# the global components, in the right order. For example, if we have this
	# global hierarchy:
	#  GSM
	#  \
	#	S1
	#    \
	#	  S2
	# and in the database we have the nti.dataserver and root persistent site managers,
	# then when we create the persistent sites for S1 and S2 (PS1 and PS2) we want the resolution order
	# to be:
	#   PS2 -> S2 -> PS1 -> S1 -> DS -> Root -> GSM
	# That is, we need to get the persistent components mixed in between the
	# global components.
	# Fortunately this is very easy to achieve. The code in zope.interface.ro handles this.
	# We just need to ensure:
	#   PS1.__bases__ = (S1, DS)
	#   PS2.__bases__ = (S2, PS1)

	sites = component.getUtility(IEtcNamespace, name='hostsites')
	ds_folder = sites.__parent__
	assert IDataserverFolder.providedBy(ds_folder)

	ds_site_manager = ds_folder.getSiteManager()

	# Ok, find everything that is globally registered
	all_global_named_utilities = list(component.getGlobalSiteManager().getUtilitiesFor(IComponents))
	for name, comp in all_global_named_utilities:
		# The sites must be registered the same as their internal name
		assert name == comp.__name__
	all_global_utilities = [x[1] for x in all_global_named_utilities]

	# Now, get the resolution order of each site; this is an easy way
	# to do a kind of topological sort.
	site_ros = [ro.ro(x) for x in all_global_utilities]

	# Next, start creating persistent sites in the database, walking from the top
	# of the resolution order (the end of the list)
	# towards the root; the first one we put in the DB gets the DS as its
	# base, otherwise it gets the previous one we put in.

	for site_ro in site_ros:
		site_ro = reversed(site_ro)

		secondary_comps = ds_site_manager
		for comps in site_ro:
			name = comps.__name__
			logger.debug("Checking host policy for site %s", name)
			if name.endswith('base') or name.startswith('base'):
				# The GSM or the base global objects
				# TODO: better way to do this...marker interface?
				continue
			if name in sites:
				logger.debug("Host policy for %s already in place", name)
				# Ok, we've already put one in for this level.
				# We need to make it our next choice going forward
				secondary_comps = sites[name].getSiteManager()
			else:
				# Great, create the site
				logger.info("Installing site policy %s", name)

				site = HostPolicyFolder()
				# should fire object created event
				sites[name] = site

				site_policy = HostPolicySiteManager(site)
				site_policy.__bases__ = (comps, secondary_comps)
				# should fire INewLocalSite
				site.setSiteManager(site_policy)
				secondary_comps = site_policy

from zope.site.interfaces import INewLocalSite
@component.adapter(INewLocalSite)
def new_local_site_dispatcher(event):
	"""
	Dispatches just like an object event,
	that way we can do things based on the type of the
	site manager.

	Note that if the containing ISite is (re)moved, an
	ObjectEvent will be fired for (sitemanager, site-event);
	that is, you subscribe to the site manager and the object moved
	event, but the event will have the ISite as the object property.
	"""
	component.handle(event.manager, event)

def run_job_in_all_host_sites(func):
	"""
	While already operating inside of a transaction and the dataserver
	environment, execute the callable given by ``func`` once for each
	persistent, registered host (see ;func:`synchronize_host_policies`).
	The callable is run with that site current.

	The order in which sites are accessed is top-down breadth-first,
	that is, the shallowest to the deepest nested sites. This allows
	you to assume that your parent sites have already been updated.

	This is typically used to make configuration changes/adjustments
	to utilities local within each site, while the appropriate event
	listeners for the site also fire.

	You are responsible for transaction management.

	:raises: Whatever the callable raises.
	:returns: A list of pairs `(site, result)` containing each site
		and the result of running the function in that site.
	:rtype: list
	"""

	sites = component.getUtility(IEtcNamespace, name='hostsites')
	sites = list(sites.values())
	logger.debug("Asked to run job %s in sites %s", func, sites)

	# The easyiest way to go top-down is to again use the resolution order;
	# we just have to watch out for duplicates and non-persistent components
	site_to_ro = {site: ro.ro(site.getSiteManager()) for site in sites}

	# This should be a plain, directed acyclic tree (single root) that is now
	# linearized.
	# Transform from the site manager back into the site object itself
	site_to_site_ro = {}
	for site, managers in site_to_ro.items():
		site_to_site_ro[site] = [getattr(x, '__parent__', None) for x in managers]

	# Ok, now, go through the dictionary, walking from the top to the bottom,
	# one at a time, thus producing the correct order
	# (Because our datastructure looks like this:
	#   site1: [site1, ds, base, GSM]
	#   site2: [site2, site1, base, GSM]
	#   site3: [site3, ds, base, GSM])
	ordered = list()

	while site_to_site_ro:
		for site, managers in dict(site_to_site_ro).items():
			if not managers:
				site_to_site_ro.pop(site)
				continue

			base_site = managers.pop()
			if base_site in sites and base_site not in ordered:
				# Ie., it's a real one we haven't seen before
				ordered.append( base_site )

	results = list()
	for site in ordered:
		logger.debug('Running job %s in site %s', func, site.__name__)
		with current_site(site):
			result = func()
			results.append( (site, result) )

	return results


## Legacy notes:
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
