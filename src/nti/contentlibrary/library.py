#!/Sr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes useful for working with libraries.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import numbers

from zope import interface
from zope import lifecycleevent
from zope.event import notify

from . import interfaces

from nti.utils.property import alias

from abc import ABCMeta
import warnings

@interface.implementer(interfaces.ISyncableContentPackageLibrary)
class AbstractLibrary(object):
	"""
	Base class for a Library.

	To make this library concrete, you must implement the
	abstract methods. This implementation only depends upon those,
	and the resulting value for ``contentPackages``.
	"""

	__metaclass__ = ABCMeta

	#: Placeholder for prefixes that should be applied when generating
	#: URLs for items in this library.
	url_prefix = ''

	#: A place where we will cache the list of known
	#: content packages. A value of `None` means we have never
	#: been synced. The behaviour of iterating content packages
	#: to implicitly sync is deprecated.
	_contentPackages = None

	__name__ = 'Library'
	__parent__ = None

	def __init__(self, prefix='', **kwargs):
		if prefix:
			self.url_prefix = prefix

	def _package_factory(self, possible_content_package):
		"""A callable object that is passed each item from :attr:`possible_content_packages`
		and returns either a package factory, or `None`.

		This should not file the ``created`` event.
		"""
		return None

	def _possible_content_packages(self):
		"""
		A sequence of objects to introspect for :class:`.IContentPackage` objects;
		typically strings. These are passed to :attr:`package_factory`
		"""
		return ()

	def _syncContentPackages(self):
		"""
		Returns a sequence of IContentPackage items, as created by
		invoking the ``self._package_factory`` on each item returned
		from iterating across ``self._possible_content_packages``.
		"""
		titles = []
		for path in self._possible_content_packages():
			title = self._package_factory( path )
			if title:
				title.__parent__ = self
				titles.append( title )
		return titles

	def syncContentPackages(self):
		"""
		Fires created, added, modified, or removed events for each
		content package, as appropriate.
		"""
		never_synced = self._contentPackages is None
		old_content_packages = list(self._contentPackages or ())

		new_content_packages = list(self._syncContentPackages())
		# Before we fire any events, compute all the work so that
		# we can present a consistent view to any listeners that
		# will be watching

		removed = []
		added = []
		changed = []
		unmodified = []

		for new in new_content_packages:
			if new not in old_content_packages:
				added.append(new)
		for old in old_content_packages:
			new = None
			for x in new_content_packages:
				if x == old:
					new = x
					break
			if new is None:
				removed.append(old)
			elif old.lastModified < new.lastModified:
				changed.append(new)
			else:
				unmodified.append(old)

		# now set up our view of the world
		_contentPackages = []
		_contentPackages.extend(added)
		_contentPackages.extend(unmodified)

		self._contentPackages = tuple(_contentPackages)

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
		for up in changed:
			lifecycleevent.modified(up)
		for new in added:
			lifecycleevent.created(new)
			lifecycleevent.added(new)

		if removed or added or changed or never_synced:
			attributes = lifecycleevent.Attributes(interfaces.IContentPackageLibrary,
												   'contentPackages')
			event = interfaces.ContentPackageLibrarySynchedEvent(self, attributes)

			notify(event)

	@property
	def contentPackages(self):
		if self._contentPackages is None:
			warnings.warn("Please sync the library first.")
			self.syncContentPackages()
		return self._contentPackages

	def __delattr__(self, name):
		"""
		As a nuclear option, you can delete the property `contentPackages`
		to enforce a complete removal of the entire value, and the next
		sync will be from scratch.
		"""
		if name == 'contentPackages' and '_contentPackages' in self.__dict__:
			# When we are uncached to force re-enumeration,
			# we need to send the corresponding object removed events
			# so that people that care can clean up
			for title in self._contentPackages:
				lifecycleevent.removed(title)
			name = '_contentPackages'
		super(AbstractLibrary,self).__delattr__(name)

	titles = alias('contentPackages' )
	createdTime = 0

	@property
	def lastModified(self):
		"""
		This object is deemed to be last modified at least
		as recently as any of its content packages.
		Note: This fails if removal is supported by the subclass (last modified could go
		backwards). If you support removal, you should override this
		method.
		"""
		mods = [x.index_last_modified for x in self.contentPackages if x.index_last_modified is not None]
		return max(mods) if mods else -1

	def __getitem__( self, key ):
		"""
		:return: The LibraryEntry having a name or ntiid that matches `key`.
		"""
		if isinstance(key,numbers.Integral):
			return self.contentPackages[key]

		for title in self.contentPackages:
			if key in (title.title, title.ntiid):
				return title
		raise KeyError( key )

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
		return len(self.contentPackages)
	def __contains__( self, key ):
		return self.get( key ) is not None

	def pathToNTIID(self, ntiid):
		""" Returns a list of TOCEntry objects in order until
		the given ntiid is encountered, or None of the id cannot be found."""
		for title in self.contentPackages:
			result = pathToPropertyValue( title, 'ntiid', ntiid )
			if result:
				return result
		return None

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

class EmptyLibrary(AbstractLibrary):
	"""
	A library that is perpetually empty.
	"""

	def __init__(self, prefix=''):
		super(EmptyLibrary,self).__init__(prefix=prefix)

	def _syncContentPackages(self):
		return ()

def pathToPropertyValue( unit, prop, value ):
	"""
	A convenience function for returning, in order from the root down,
	the sequence of children required to reach one with a property equal to
	the given value.
	"""
	if getattr( unit, prop, None ) == value:
		return [unit]
	for child in unit.children:
		childPath = pathToPropertyValue( child, prop, value )
		if childPath:
			# We very inefficiently append to the front
			# each time, rather than trying to find when recursion ends
			# and reverse
			childPath.insert( 0, unit )
			return childPath
	return None
