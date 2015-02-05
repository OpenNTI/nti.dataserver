#!/Sr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes useful for working with libraries.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import numbers
import warnings

from repoze.lru import LRUCache

from ZODB.POSException import POSError
from ZODB.interfaces import IConnection, IBroken

import zope.intid
from zope import component
from zope import interface
from zope import lifecycleevent

from zope.event import notify
from zope.annotation.interfaces import IAttributeAnnotatable

from persistent import Persistent

from nti.common.property import alias
from nti.common.property import CachedProperty

from nti.externalization.persistence import NoPickle

from nti.ntiids.ntiids import ROOT as NTI_ROOT

from nti.site.localutility import queryNextUtility

from .interfaces import IContentPackageLibrary
from .interfaces import IPersistentContentUnit
from .interfaces import IContentPackageEnumeration
from .interfaces import ContentPackageReplacedEvent
from .interfaces import ISyncableContentPackageLibrary
from .interfaces import ContentPackageLibraryDidSyncEvent
from .interfaces import ContentPackageLibraryWillSyncEvent
from .interfaces import ContentPackageLibraryModifiedOnSyncEvent
from .interfaces import IDelimitedHierarchyContentPackageEnumeration

@interface.implementer(IContentPackageEnumeration)
class AbstractContentPackageEnumeration(object):
	"""
	Base class providing some semantic helpers for enumeration.

	In any case, to make this class concrete, see
	:meth:`_package_factory` and :meth:`_possible_content_packages`.

	"""

	__name__ = None
	__parent__ = None

	def _package_factory(self, possible_content_package):
		"""A callable object that is passed each item from :attr:`possible_content_packages`
		and returns either a package factory, or `None`.

		This should not fire the ``created`` event.
		"""
		return None

	def _possible_content_packages(self):
		"""
		A sequence of objects to introspect for :class:`.IContentPackage` objects;
		typically strings. These are passed to :attr:`package_factory`
		"""
		return ()

	def enumerateContentPackages(self):
		"""
		Returns a sequence of IContentPackage items, as created by
		invoking the ``self._package_factory`` on each item returned
		from iterating across ``self._possible_content_packages``.
		"""
		titles = []
		for path in self._possible_content_packages():
			title = self._package_factory( path )
			if title:
				titles.append( title )
		return titles

@interface.implementer(IDelimitedHierarchyContentPackageEnumeration)
class AbstractDelimitedHiercharchyContentPackageEnumeration(AbstractContentPackageEnumeration):
	"""
	An object that works with a root bucket to enumerate content paths.
	We override :meth:`_possible_content_packages`, you still
	need to override :meth:`_package_factory` at a minimum.
	"""

	root = None

	def _possible_content_packages(self):
		"""
		Returns the children of the root.
		"""

		root = self.root
		if root is None:
			return ()
		return root.enumerateChildren()

def _register_units( content_unit ):
	"""
	Recursively register content units.
	"""
	intids = component.queryUtility( zope.intid.IIntIds )
	if intids is None:
		return
	
	def _register( obj ):
		try:
			if IBroken.providedBy(obj) or not IPersistentContentUnit.providedBy(obj):
				return
			intid = intids.queryId( obj )
			if intid is None:
				intids.register( obj )
		except (TypeError, POSError): # Broken object
			return
		for child in obj.children:
			_register( child )
	_register( content_unit )

def _unregister_units( content_unit ):
	"""
	Recursively unregister content units.
	"""
	intids = component.queryUtility( zope.intid.IIntIds )
	if intids is None:
		return
	
	def _unregister( obj ):
		intid = None
		try:
			if IBroken.providedBy(obj) or not IPersistentContentUnit.providedBy(obj):
				return
			intid = intids.queryId( obj )
			if intid is not None:
				intids.unregister( obj )
		except (TypeError, POSError): # Broken object
			pass
		for child in obj.children:
			_unregister( child )
	_unregister( content_unit )

@interface.implementer(ISyncableContentPackageLibrary)
class AbstractContentPackageLibrary(object):
	"""
	A library that uses an enumeration and cooperates with parent
	libraries in the component hierarchy to build a complete
	library.

	We become the parent of the enumeration, so it is critical that
	enumerations are not shared between libraries; an enumeration
	defines a library, so those libraries would be semantically
	equivalent.
	"""

	#: Placeholder for prefixes that should be applied when generating
	#: URLs for items in this library.
	url_prefix = ''

	#: A place where we will cache the list of known
	#: content packages. A value of `None` means we have never
	#: been synced. The behaviour of iterating content packages
	#: to implicitly sync is deprecated.
	_contentPackages = None

	#: The enumeration we will use when asked to sync
	#: content packages.
	_enumeration = None

	#: When we sync, we capture the `lastModified` timestamp
	#: of the enumeration, if it provides it.
	_enumeration_last_modified = 0

	__name__ = 'Library'
	__parent__ = None

	def __init__(self, enumeration, prefix='', **kwargs):
		self._enumeration = enumeration
		enumeration.__parent__ = self
		assert enumeration is not None
		if prefix:
			self.url_prefix = prefix

	def syncContentPackages(self):
		"""
		Fires created, added, modified, or removed events for each
		content package, as appropriate.
		"""
		notify(ContentPackageLibraryWillSyncEvent(self))

		never_synced = self._contentPackages is None
		old_content_packages = list(self._contentPackages or ())
		old_content_packages_by_ntiid = {x.ntiid: x for x in old_content_packages}

		new_content_packages = list(self._enumeration.enumerateContentPackages())

		new_content_packages_by_ntiid = {x.ntiid: x for x in new_content_packages}
		assert len(new_content_packages) == len(new_content_packages_by_ntiid), "Invalid library"
		enumeration_last_modified = getattr(self._enumeration, 'lastModified', 0)

		# Before we fire any events, compute all the work so that
		# we can present a consistent view to any listeners that
		# will be watching
		removed = []
		changed = []
		unmodified = []
		added = [package
				 for ntiid, package in new_content_packages_by_ntiid.items()
				 if ntiid not in old_content_packages_by_ntiid]

		for old in old_content_packages:
			new = new_content_packages_by_ntiid.get(old.ntiid)

			if new is None:
				removed.append(old)
			elif old.lastModified < new.lastModified:
				changed.append( (new, old) )
			else:
				unmodified.append(old)

		something_changed = removed or added or changed

		# now set up our view of the world
		_contentPackages = []
		_contentPackages.extend(added)
		_contentPackages.extend(unmodified)
		_contentPackages.extend([x[0] for x in changed])

		_contentPackages = tuple(_contentPackages)
		_content_packages_by_ntiid = {x.ntiid: x for x in _contentPackages}
		assert len(_contentPackages) == len(_content_packages_by_ntiid), "Invalid library"

		if something_changed or never_synced:
			# XXX CS/JZ, 1-29-15 We need this before event firings because some code
			# (at least question_map.py used to) relies on getting the new content units
			# via pathToNtiid.
			# TODO: Verify nothing else is doing so.
			self._contentPackages = _contentPackages
			self._enumeration_last_modified = enumeration_last_modified
			self._content_packages_by_ntiid = _content_packages_by_ntiid

			if not never_synced:
				logger.info("Library %s adding packages %s", self, added)
				logger.info("Library %s removing packages %s", self, removed)
				logger.info("Library %s changing packages %s", self, changed)

			# Now fire the events letting listeners (e.g., index and question adders)
			# know that we have content. Randomize the order of this across worker
			# processes so that we don't collide too badly on downloading indexes if need be
			# (only matters if we are not preloading).
			# Do this in greenlets/parallel. This can radically speed up
			# S3 loading when we need the network.
			# XXX: Does order matter?
			# XXX: Note that we are not doing it in parallel, because if we need
			# ZODB site access, we can have issues. Also not we're not
			# randomizing because we expect to be preloaded.
			for old in removed:
				lifecycleevent.removed(old)
				_unregister_units(old)
				old.__parent__ = None

			for new, old in changed:
				new.__parent__ = self
				# new is a created object
				IConnection( self ).add( new )
				# XXX CS/JZ, 2-04-15 DO NEITHER call lifecycleevent.created nor
				# lifecycleevent.added on 'new' objects as modified events subscribers
				# are expected to handle any change
				_register_units( new )
				# Note that this is the special event that shows both objects.
				notify(ContentPackageReplacedEvent(new, old))

			for new in added:
				new.__parent__ = self
				lifecycleevent.created(new)
				lifecycleevent.added(new)
				_register_units( new )

			# after updating remove parent reference for old objects
			for _, old in changed:
				# XXX CS/JZ, 2-04-15  DO NOT call lifecycleevent.removed on this
				# objects b/c this may unregister things we don't want to leaving
				# the database in a invalid state
				_unregister_units(old)
				old.__parent__ = None

			# Ok, new let people know that 'contentPackages' changed
			attributes = lifecycleevent.Attributes(IContentPackageLibrary, 'contentPackages')
			event = ContentPackageLibraryModifiedOnSyncEvent(self, attributes)
			notify(event)

		# Finish up by saying that we sync'd, even if nothing changed
		notify(ContentPackageLibraryDidSyncEvent(self))

		self._enumeration.lastSynchronized = time.time()
		if something_changed or never_synced:
			self._clear_caches()

	#: A map from top-level content-package NTIID to the content package.
	#: This is cached based on the value of the _contentPackages variable,
	#: and uses that variable, which must not be modified outside the
	#: confines of this class.
	_content_packages_by_ntiid = ()

	@property
	def contentPackages(self):
		if self._contentPackages is None:
			warnings.warn("Please sync the library first.", stacklevel=2)
			warnings.warn("Please sync the library first.", stacklevel=3)
			self.syncContentPackages()

		# We would like to use a generator here, to avoid
		# copying in case of a parent, but our interface
		# requires that this be indexable, for some reason.
		# Note that our values always take precedence over anything
		# we get from the parent
		parent = queryNextUtility(self, IContentPackageLibrary)
		if parent is None:
			# We can directly return our tuple, yay
			return self._contentPackages

		contentPackages = list(self._contentPackages)
		for i in parent.contentPackages:
			if i.ntiid not in self._content_packages_by_ntiid:
				contentPackages.append(i)
		return contentPackages

	def __delattr__(self, name):
		"""
		As a nuclear option, you can delete the property `contentPackages`
		to enforce a complete removal of the entire value, and the next
		sync will be from scratch.
		"""
		if name == 'contentPackages':
			self.resetContentPackages()
		else:
			super(AbstractContentPackageLibrary,self).__delattr__(name)

	titles = alias('contentPackages')

	def resetContentPackages(self):
		"""
		As a nuclear option, this enforces a complete removal of all
		the packages directly stored here. The next sync will be from
		scratch.
		"""

		try:
			# let subclasses be persistent
			self._p_activate()
		except AttributeError:
			pass

		if '_contentPackages' not in self.__dict__:
			return

		# When we are uncached to force re-enumeration,
		# we need to send the corresponding object removed events
		# so that people that care can clean up.
		# TODO: What's the right order for this, before or after
		# we do the delete?
		for title in self._contentPackages:
			lifecycleevent.removed(title)
			_unregister_units(title)
			title.__parent__ = None

		# Must also take care to clear its dependents
		if '_content_packages_by_ntiid' in self.__dict__:
			del self._content_packages_by_ntiid
		del self._contentPackages

	@property
	def createdTime(self):
		return getattr(self._enumeration, 'createdTime', 0)

	@property
	def lastModified(self):
		"""
		This object is deemed to be last modified at least
		as recently as any of its content packages and its enumeration.
		Note: This fails if removal is supported by the subclass (last modified could go
		backwards). If you support removal, you should override this
		method.
		"""
		# Refuse to do this if we're not sync'd!
		if self._contentPackages is None:
			return -1

		lastModified = -1
		for x in self.contentPackages:
			lastModified = max(lastModified, x.index_last_modified or -1)

		lastModified = max(self._enumeration_last_modified, lastModified)
		return lastModified

	def __getitem__( self, key ):
		"""
		:return: The LibraryEntry having an ntiid that matches `key`.
		"""
		if isinstance(key,numbers.Integral):
			if key != 0:
				raise TypeError("Integers other than 0---first---not supported")
			# This should only be done by tests

			return list(self.contentPackages)[key]

		# In the past this worked even if the library
		# had not been synced because it used self.contentPackages
		# to do the implicit sync
		if key in self._content_packages_by_ntiid:
			return self._content_packages_by_ntiid[key]

		# We no longer check titles
		parent = queryNextUtility(self, IContentPackageLibrary)
		if parent is None:
			raise KeyError( key )

		return parent.__getitem__(key)

	def get( self, key, default=None ):
		try:
			return self[key]
		except KeyError:
			return default

	# Other container methods
	def __delitem__( self, key ):
		raise TypeError("deletion not supported")
	def __setitem__( self, key ):
		raise TypeError("setting not supported" )
	def __len__( self ):
		# XXX: This doesn't make much sense
		return len(self._content_packages_by_ntiid)
	def __contains__( self, key ):
		return self.get( key ) is not None

	def __bool__(self):
		# We are always true, regardless of content
		return True
	__nonzero__ = __bool__

	@property
	def lastSynchronized(self):
		result = getattr(self._enumeration, 'lastSynchronized', 0)
		return result

	@CachedProperty("lastSynchronized")
	def _v_path_to_ntiid_cache(self):
		result = LRUCache(2000)
		return result

	def _clear_caches(self):
		self._v_path_to_ntiid_cache.clear()

	def pathToNTIID(self, ntiid):
		"""
		 Returns a list of TOCEntry objects in order until
		the given ntiid is encountered, or None of the id cannot be found.
		"""
		# We store as weak refs to avoid ConnectionStateErrors
		# and to reduce memory usage.
		# TODO We could increase this cache size if it's extremely small,
		# as expected.
		result = self._v_path_to_ntiid_cache.get(ntiid)
		if result:
			return [x() for x in result]
		elif result is not None:
			# Empty list
			return None

		# We special case the root ntiid by only looking in
		# the top level of content packages for our ID.  We should
		# always return None unless there are root content prefs.
		if ntiid == NTI_ROOT:
			for title in self.contentPackages:
				if getattr( title, 'ntiid', None ) == ntiid:
					result = [title]
					break
		else:
			for title in self.contentPackages:
				vals = _pathToPropertyValue( title, 'ntiid', ntiid )
				if vals:
					result = vals
					break

		if result:
			cache_val = [_PathCacheContentUnitWeakRef(x) for x in result]
			self._v_path_to_ntiid_cache.put( ntiid, cache_val )
		else:
			# Make sure we don't lose these worst-cases.
			self._v_path_to_ntiid_cache.put( ntiid, [] )
		return result

	def childrenOfNTIID( self, ntiid ):
		"""
		Returns a flattened list of all the children entries of ntiid in
		no particular order. If there are no children, returns an empty list.

		:return: Always returns a fresh list.
		"""
		path = self.pathToNTIID( ntiid )
		result = []
		if path:
			parent = path[-1]
			def rec(toc,accum):
				for child in toc.children:
					rec( child, accum )
				accum.append( toc )
			rec( parent, result )
			# And the last thing we did was append the parent
			# itself, so take it off; we only want the children
			result.pop()
		return result

	def pathsToEmbeddedNTIID(self, ntiid):
		"""
		Returns a list of paths (sequences of TOCEntry objects); the last
		element in each path is a :class:`.IContentUnit` that contains an
		embedded reference to the given NTIID. That is, the returned list
		describes all the locations that the NTIID is known to be referenced
		for use as a subcontainer. The returned list of paths is in no
		particular order.
		"""
		result = []
		def rec(unit):
			if ntiid in unit.embeddedContainerNTIIDs:
				result.append( self.pathToNTIID( unit.ntiid ) )
			for child in unit.children: # it is even possible to embed the thing twice within a hierarchy
				rec(child)

		for package in self.contentPackages:
			rec(package)
		return result

def _pathToPropertyValue( unit, prop, value ):
	"""
	A convenience function for returning, in order from the root down,
	the sequence of children required to reach one with a property equal to
	the given value.
	"""
	results = __pathToPropertyValue( unit, prop, value )
	if results:
		results.reverse()
	return results

def __pathToPropertyValue( unit, prop, value ):
	if getattr( unit, prop, None ) == value:
		return [unit]

	for child in unit.children:
		childPath = __pathToPropertyValue( child, prop, value )
		if childPath:
			childPath.append( unit )
			return childPath
	return None

@interface.implementer(IAttributeAnnotatable)
@NoPickle
class GlobalContentPackageLibrary(AbstractContentPackageLibrary):
	"""
	A content package library meant only to be installed in the global
	(non-persistent) registry. This type of library must be synchronized
	on every startup.
	"""

class _EmptyEnumeration(AbstractContentPackageEnumeration):

	def enumerateContentPackages(self):
		return ()

def EmptyLibrary(prefix=''):
	"""
	A library that is perpetually empty.
	"""
	return GlobalContentPackageLibrary(_EmptyEnumeration(), prefix=prefix)

class PersistentContentPackageLibrary(Persistent,
									  AbstractContentPackageLibrary):
	"""
	A library that is meant to be persisted. It
	generally does not need to be synchronized on
	every startup, only when content on disk has changed.
	"""

from zope.interface.interfaces import ComponentLookupError
from nti.intid.interfaces import IntIdMissingError
from nti.schema.schema import EqHash

@EqHash('_obj', '_intid')
class _PathCacheContentUnitWeakRef(object):
	"""
	A specific wref designed just for pathToNtiid caching.
	We cannot use the existing ContentUnitWeakRef because
	at sync time, we rely on content packages changing
	underneath bundles and via wref, being resolved through
	the library.
	"""

	__slots__ = (b'_intid', b'_obj')

	def __init__(self, contentunit):
		self._obj = None
		self._intid = None

		try:
			intids = component.getUtility( zope.intid.IIntIds )
			self._intid = intids.getId( contentunit )
		except (IntIdMissingError,ComponentLookupError):
			# For non-persistant cases (or unit tests), store the object itself.
			# These should be rare.
			self._obj = contentunit

	def __call__(self):
		if self._obj is not None:
			result = self._obj
		else:
			intids = component.getUtility( zope.intid.IIntIds )
			result = intids.getObject( self._intid )

		return result
