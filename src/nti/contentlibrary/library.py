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

from BTrees.OOBTree import OOBTree

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.event import notify

from zope.intid.interfaces import IIntIds

from ZODB.interfaces import IBroken
from ZODB.interfaces import IConnection

from ZODB.POSException import POSError
from ZODB.POSException import ConnectionStateError

from persistent import Persistent

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IGlobalContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IPersistentContentUnit
from nti.contentlibrary.interfaces import ContentPackageAddedEvent
from nti.contentlibrary.interfaces import ContentPackageRemovedEvent
from nti.contentlibrary.interfaces import IContentPackageEnumeration
from nti.contentlibrary.interfaces import ContentPackageReplacedEvent
from nti.contentlibrary.interfaces import ContentPackageUnmodifiedEvent
from nti.contentlibrary.interfaces import ISyncableContentPackageLibrary
from nti.contentlibrary.interfaces import ContentPackageLibraryDidSyncEvent
from nti.contentlibrary.interfaces import ContentPackageLibraryWillSyncEvent
from nti.contentlibrary.interfaces import ContentPackageLibraryModifiedOnSyncEvent
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentPackageEnumeration

from nti.contentlibrary.synchronize import SynchronizationResults
from nti.contentlibrary.synchronize import ContentRemovalException
from nti.contentlibrary.synchronize import UnmatchedRootNTIIDException
from nti.contentlibrary.synchronize import LibrarySynchronizationResults

from nti.externalization.persistence import NoPickle

from nti.property.property import Lazy
from nti.property.property import alias

from nti.site.localutility import queryNextUtility

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
			title = self._package_factory(path)
			if title:
				titles.append(title)
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

def _register_content_units(context, content_unit):
	"""
	Recursively register content units.
	"""
	intids = component.queryUtility(IIntIds)
	if intids is None:
		return

	def _register(obj):
		_add_2_connection(context, obj)
		try:
			if 		IBroken.providedBy(obj) or \
				not IPersistentContentUnit.providedBy(obj):
				return
			intid = intids.queryId(obj)
			if intid is None:
				intids.register(obj)
		except (TypeError, POSError):  # Broken object
			return
		for child in obj.children:
			_register(child)
	_register(content_unit)

def _unregister_content_units(content_unit):
	"""
	Recursively unregister content units.
	"""
	intids = component.queryUtility(IIntIds)
	if intids is None:
		return

	def _unregister(obj):
		intid = None
		try:
			if 	IBroken.providedBy(obj) or \
				not IPersistentContentUnit.providedBy(obj):
				return
			intid = intids.queryId(obj)
			if intid is not None:
				intids.unregister(obj)
		except (TypeError, POSError):  # Broken object
			pass
		for child in obj.children:
			_unregister(child)
	_unregister(content_unit)

def _add_2_connection(context, obj):
	connection = IConnection(context, None)
	if connection is not None and not IConnection(obj, None):
		connection.add(obj)
		return True
	return False

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

	# Placeholder for prefixes that should be applied when generating
	# URLs for items in this library.
	url_prefix = ''

	# A place where we will cache the list of known
	# content packages. A value of `None` means we have never
	# been synced. The behaviour of iterating content packages
	# to implicitly sync is deprecated.
	_contentPackages = None

	# The enumeration we will use when asked to sync
	# content packages.
	_enumeration = None

	# When we sync, we capture the `lastModified` timestamp
	# of the enumeration, if it provides it.
	_enumeration_last_modified = 0

	__name__ = 'Library'
	__parent__ = None

	def __init__(self, enumeration, prefix='', **kwargs):
		self._enumeration = enumeration
		enumeration.__parent__ = self
		assert enumeration is not None
		if prefix:
			self.url_prefix = prefix

	def _content_packages_tuple(self, contentPackages=(), packages=None):
		if not packages:
			by_list = list(contentPackages or ())
			by_ntiid = {x.ntiid: x for x in by_list}
		else:
			by_list = []
			by_ntiid = {}
			for content_package in contentPackages or ():
				if content_package.ntiid in packages:
					by_list.append(content_package)
					by_ntiid[content_package.ntiid] = content_package
			if not by_list:
				raise Exception("No package to update was found")

		return by_list, by_ntiid

	@property
	def _root_name(self):
		root = getattr(self._enumeration, 'root', None)
		name = root.__name__ if root is not None else self.__name__
		return name

	def _do_addContentPackages(self, added, lib_sync_results, params, results):
		for new in added:
			new.__parent__ = self
			_register_content_units(self, new)  # get intids
			lifecycleevent.created(new)
			lib_sync_results.added(new.ntiid)   # register
			notify(ContentPackageAddedEvent(new, params, results))

	def _do_removeContentPackages(self, removed, lib_sync_results, params, results):
		for old in removed or ():
			notify(ContentPackageRemovedEvent(old, params, results))
			_unregister_content_units(old)
			old.__parent__ = None
			lib_sync_results.removed(old.ntiid)  # register

	def _do_updateContentPackages(self, changed, lib_sync_results, params, results):
		for new, old in changed:
			# check ntiid changes
			if new.ntiid != old.ntiid:
				raise UnmatchedRootNTIIDException(
						"Pacakge NTIID changed from %s to %s" % (old.ntiid, new.ntiid))
			new.__parent__ = self
			# XXX CS/JZ, 2-04-15 DO NEITHER call lifecycleevent.created nor
			# lifecycleevent.added on 'new' objects as modified events subscribers
			# are expected to handle any change
			_register_content_units(self, new)
			lib_sync_results.modified(new.ntiid)  # register
			# Note that this is the special event that shows both objects.
			notify(ContentPackageReplacedEvent(new, old, params, results))

	def _get_content_units_by_ntiid(self, packages):
		"""
		Get our ntiid to content unit map.
		"""
		result = OOBTree()
		def _recur(unit):
			result[unit.ntiid] = unit
			for child in unit.children:
				_recur(child)
		for package in packages:
			_recur(package)
		return result

	def _do_checkContentPackages(self, added, unmodified, changed=()):
		_contentPackages = []
		_contentPackages.extend(added)
		_contentPackages.extend(unmodified)
		_contentPackages.extend(changed)

		_contentPackages = tuple(_contentPackages)
		_content_packages_by_ntiid = {x.ntiid: x for x in _contentPackages}
		_content_units_by_ntiid = self._get_content_units_by_ntiid( _contentPackages )
		assert len(_contentPackages) == len(_content_packages_by_ntiid), "Invalid library"
		return _contentPackages, _content_packages_by_ntiid, _content_units_by_ntiid

	def _do_completeSyncPackages(self, unmodified, lib_sync_results, params, results,
								 do_notify=True):
		if do_notify:
			# Signal what pacakges WERE NOT modified
			for pacakge in unmodified or ():
				notify(ContentPackageUnmodifiedEvent(pacakge, params, results))

			# Finish up by saying that we sync'd, even if nothing changed
			notify(ContentPackageLibraryDidSyncEvent(self, params, results))

		# set last sync time
		self._enumeration.lastSynchronized = time.time()
		return lib_sync_results

	def addRemoveContentPackages(self, params=None, results=None):
		"""
		Only add/remove content packages in the library
		"""
		results = SynchronizationResults() if results is None else results
		notify(ContentPackageLibraryWillSyncEvent(self, params))
		lib_sync_results = LibrarySynchronizationResults(Name=self._root_name)
		results.add(lib_sync_results)

		never_synced = self._contentPackages is None
		old_content_packages, old_content_packages_by_ntiid = \
					self._content_packages_tuple(self._contentPackages)

		contentPackages = self._enumeration.enumerateContentPackages()
		_, new_content_packages_by_ntiid = \
					self._content_packages_tuple(contentPackages)

		added = [package
			 		for ntiid, package in new_content_packages_by_ntiid.items()
			 		if ntiid not in old_content_packages_by_ntiid]

		removed = []
		unmodified = []
		for old in old_content_packages:
			new = new_content_packages_by_ntiid.get(old.ntiid)
			if new is None:
				removed.append(old)
			else:
				unmodified.append(old)

		something_changed = removed or added

		# now set up our view of the world
		_contentPackages, _content_packages_by_ntiid, _content_units_by_ntiid = \
									self._do_checkContentPackages(added, unmodified, ())

		if something_changed or never_synced:
			enumeration_last_modified = getattr(self._enumeration, 'lastModified', 0)
			# CS/JZ, 1-29-15 We need this before event firings because some code
			# (at least question_map.py used to) relies on getting the new content units
			# via pathToNtiid.
			# TODO: Verify nothing else is doing so.
			self._contentPackages = _contentPackages
			self._enumeration_last_modified = enumeration_last_modified
			self._content_packages_by_ntiid = _content_packages_by_ntiid
			self._content_units_by_ntiid = _content_units_by_ntiid

			if not never_synced:
				logger.info("Library %s adding packages %s", self, added)
				logger.info("Library %s removing packages %s", self, removed)

			if removed and params != None and not params.allowRemoval:
				raise ContentRemovalException(
							"Cannot remove content pacakges without explicitly allowing it")

			self._do_removeContentPackages(removed, lib_sync_results, params, results)

			self._do_addContentPackages(added, lib_sync_results, params, results)

		do_event = bool(something_changed or never_synced)
		self._do_completeSyncPackages(unmodified,
									  lib_sync_results,
									  params,
									  results,
									  do_event)
		return lib_sync_results

	def syncContentPackages(self, params=None, results=None):
		"""
		Fires created, added, modified, or removed events for each
		content package, as appropriate.
		"""
		packages = params.ntiids if params is not None else ()
		results = SynchronizationResults() if results is None else results
		notify(ContentPackageLibraryWillSyncEvent(self, params))

		lib_sync_results = LibrarySynchronizationResults(Name=self._root_name)
		results.add(lib_sync_results)

		# filter packages if specified
		never_synced = self._contentPackages is None
		filtered_old_content_packages, filtered_old_content_packages_by_ntiid = \
						self._content_packages_tuple(self._contentPackages, packages)

		# make sure we get ALL packages
		contentPackages = self._enumeration.enumerateContentPackages()
		new_content_packages, new_content_packages_by_ntiid = \
						self._content_packages_tuple(contentPackages)
		assert 	len(new_content_packages) == len(new_content_packages_by_ntiid), \
				"Invalid library"
		enumeration_last_modified = getattr(self._enumeration, 'lastModified', 0)

		# Before we fire any events, compute all the work so that
		# we can present a consistent view to any listeners that
		# will be watching
		removed = []
		changed = []
		if not packages:  # no filter
			unmodified = []
			added = [package
				 		for ntiid, package in new_content_packages_by_ntiid.items()
				 		if ntiid not in filtered_old_content_packages_by_ntiid]
		else:
			# chosing this path WILL NOT add any new package
			added = ()
			unfiltered_content_packages, _ = \
						self._content_packages_tuple(self._contentPackages)

			# make sure we get old references
			unmodified = [package
				 			for package in unfiltered_content_packages
				 			if package.ntiid not in filtered_old_content_packages_by_ntiid]

		for old in filtered_old_content_packages:
			new = new_content_packages_by_ntiid.get(old.ntiid)
			if new is None:
				removed.append(old)
			elif old.lastModified < new.lastModified:
				changed.append((new, old))
			else:
				unmodified.append(old)

		something_changed = removed or added or changed

		# now set up our view of the world
		_contentPackages, _content_packages_by_ntiid, _content_units_by_ntiid = \
									self._do_checkContentPackages(added,
																  unmodified,
																  [x[0] for x in changed])

		if something_changed or never_synced:
			# CS/JZ, 1-29-15 We need this before event firings because some code
			# (at least question_map.py used to) relies on getting the new content units
			# via pathToNtiid.
			# TODO: Verify nothing else is doing so.
			self._contentPackages = _contentPackages
			self._enumeration_last_modified = enumeration_last_modified
			self._content_packages_by_ntiid = _content_packages_by_ntiid
			self._content_units_by_ntiid = _content_units_by_ntiid

			if not never_synced:
				logger.info("Library %s adding packages %s", self, added)
				logger.info("Library %s removing packages %s", self, removed)
				logger.info("Library %s changing packages %s", self, changed)

			if removed and params != None and not params.allowRemoval:
				raise ContentRemovalException(
						"Cannot remove content pacakges without explicitly allowing it")

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
			self._do_removeContentPackages(removed, lib_sync_results, params, results)

			self._do_updateContentPackages(changed, lib_sync_results, params, results)

			self._do_addContentPackages(added, lib_sync_results, params, results)

			# after updating remove parent reference for old objects
			for _, old in changed:
				# CS/JZ, 2-04-15  DO NOT call lifecycleevent.removed on this
				# objects b/c this may unregister things we don't want to leaving
				# the database in a invalid state
				_unregister_content_units(old)
				old.__parent__ = None

			# Ok, new let people know that 'contentPackages' changed
			attributes = lifecycleevent.Attributes(IContentPackageLibrary, 'contentPackages')
			event = ContentPackageLibraryModifiedOnSyncEvent(self, params, results, attributes)
			notify(event)

		self._do_completeSyncPackages(unmodified,
									  lib_sync_results,
									  params,
									  results)
		return lib_sync_results

	# Maps from top-level content-package NTIIDs to the content package.
	# This is cached based on the value of the _contentPackages variable,
	# and uses that variable, which must not be modified outside the
	# confines of this class.
	_content_packages_by_ntiid = ()

	def _get_contentPackages(self):
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

	@property
	def contentPackages(self):
		return self._get_contentPackages()

	@Lazy
	def _content_units_by_ntiid(self):
		result = self._get_content_units_by_ntiid( self.contentPackages )
		return result

	def __delattr__(self, name):
		"""
		As a nuclear option, you can delete the property `contentPackages`
		to enforce a complete removal of the entire value, and the next
		sync will be from scratch.
		"""
		if name == 'contentPackages':
			self.resetContentPackages()
		else:
			super(AbstractContentPackageLibrary, self).__delattr__(name)

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
			_unregister_content_units(title)
			title.__parent__ = None # ground

		# Must also take care to clear its dependents
		if '_content_packages_by_ntiid' in self.__dict__:
			del self._content_packages_by_ntiid
		if '_content_units_by_ntiid' in self.__dict__:
			del self._content_units_by_ntiid
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

	def __getitem__(self, key):
		"""
		:return: The LibraryEntry having an ntiid that matches `key`.
		"""
		if isinstance(key, numbers.Integral):
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
			raise KeyError(key)

		return parent.__getitem__(key)

	def get(self, key, default=None):
		try:
			return self[key]
		except KeyError:
			return default

	# Other container methods
	def __delitem__(self, key):
		raise TypeError("deletion not supported")

	def __setitem__(self, key):
		raise TypeError("setting not supported")

	def __len__(self):
		# XXX: This doesn't make much sense
		return len(self._content_packages_by_ntiid)

	def __contains__(self, key):
		return self.get(key) is not None

	def __bool__(self):
		# We are always true, regardless of content
		return True
	__nonzero__ = __bool__

	@property
	def lastSynchronized(self):
		result = getattr(self._enumeration, 'lastSynchronized', 0)
		return result

	def _get_content_unit( self, key ):
		"""
		Fetch the content unit referenced by the given ntiid.
		"""
		result = self._content_units_by_ntiid.get( key )
		if result is None:
			# Check our parent
			parent = queryNextUtility(self, IContentPackageLibrary)
			if parent is not None:
				result = parent._get_content_unit( key )
		return result

	def pathToNTIID(self, ntiid):
		"""
		Returns a list of TOCEntry objects in order until
		the given ntiid is encountered, or None if the id cannot be found.
		"""
		result = None
		unit = self._get_content_unit( ntiid )
		if unit is not None:
			result = [unit]
			# Now iterate upwards and fetch our parents all the way
			# to the content package.
			def _get_parent_unit( item ):
				if IContentPackage.providedBy( item ):
					return
				parent = getattr( item, '__parent__', None )
				if parent is not None:
					result.append( parent )
					_get_parent_unit( parent )
			_get_parent_unit( unit )
			result.reverse()
		return result

	def childrenOfNTIID(self, ntiid):
		"""
		Returns a flattened list of all the children entries of ntiid in
		no particular order. If there are no children, returns an empty list.

		:return: Always returns a fresh list.
		"""
		result = []
		parent = self._get_content_unit( ntiid )
		if parent is not None:
			def rec(toc, accum):
				accum.extend(toc.embeddedContainerNTIIDs)
				for child in toc.children:
					rec(child, accum)
				accum.append(toc.ntiid)
			rec(parent, result)
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
		for unit in self._content_units_by_ntiid.values():
			if ntiid in unit.embeddedContainerNTIIDs:
				result.append(self.pathToNTIID(unit.ntiid))
		if not result:
			# Check our parent
			parent = queryNextUtility(self, IContentPackageLibrary)
			if parent is not None:
				result = parent.pathsToEmbeddedNTIID( ntiid )
		return result

@interface.implementer(IAttributeAnnotatable)
@NoPickle
class GlobalContentPackageLibrary(AbstractContentPackageLibrary):
	"""
	A content package library meant only to be installed in the global
	(non-persistent) registry. This type of library must be synchronized
	on every startup.
	"""

	def _get_contentPackages(self):
		result = super(GlobalContentPackageLibrary, self)._get_contentPackages()
		for package in result or ():
			if not IGlobalContentPackage.providedBy(package):
				interface.alsoProvides(package, IGlobalContentPackage)
		return result

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

	def __repr__(self):
		try:
			return super(PersistentContentPackageLibrary, self).__repr__()
		except ConnectionStateError:
			return object.__repr__(self)
