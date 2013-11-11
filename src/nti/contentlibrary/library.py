#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes useful for working with libraries.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#pylint: disable=E1102
import numbers

from zope import interface
from zope import lifecycleevent
from zope.cachedescriptors.property import Lazy

from . import interfaces

from nti.utils.property import alias

@interface.implementer(interfaces.IContentPackageLibrary)
class AbstractLibrary(object):
	"""
	Base class for a Library.
	"""

	#: A callable object that is passed each item from :attr:`possible_content_packages`
	#: and returns either a package factory, or `None`.
	package_factory = None

	#: A sequence of objects to introspect for :class:`.IContentPackage` objects;
	#: typically strings. These are passed to :attr:`package_factory`
	possible_content_packages = ()

	#: Placeholder for prefixes that should be applied when generating
	#: URLs for items in this library.
	url_prefix = ''

	__name__ = 'Library'
	__parent__ = None

	def __init__(self, prefix='', **kwargs):
		if prefix:
			self.url_prefix = prefix

	@property
	def contentPackages(self):
		"""
		Returns a sequence of IContentPackage items, as created by
		invoking the ``self.package_factory`` on each item returned
		from iterating across ``self.possible_content_packages``.
		"""
		titles = []
		for path in self.possible_content_packages:
			title = self.package_factory( path )
			if title:
				title.__parent__ = self
				titles.append( title )

		return titles

	titles = contentPackages # b/c

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

		for title in self.titles:
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
		for title in self.titles:
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

class AbstractStaticLibrary(AbstractLibrary):

	possible_content_packages = ()

	def __init__(self, *args, **kwargs):
		"""
		Creates a library that will examine the given paths.

		:param paths: A sequence of strings pointing to directories to introspect for
			:class:`interfaces.IContentPackage` objects.

		"""
		paths = kwargs.pop("paths", ())
		super(AbstractStaticLibrary,self).__init__(*args, **kwargs)
		if paths: # avoid overwriting a subclass's class-level property or CachedProperty
			self.possible_content_packages = paths


class AbstractCachedStaticLibrary(AbstractStaticLibrary):
	"""
	A static library that will lazily cache the results
	of enumerating the content packages.
	"""

	contentPackages = Lazy(AbstractLibrary.contentPackages.fget)
	titles = alias('contentPackages' )

class AbstractCachedNotifyingStaticLibrary(AbstractCachedStaticLibrary):
	"""
	A static library that will broadcast :class:`zope.lifecycleevent.IObjectAddedEvent`
	when content packages are added to the library (i.e., the
	first time the library's content packages are enumerated).

	In theory any library could broadcast adds and removes,
	but a non-cached library would essentially have to act as a cached
	library for that to work.

	This library currently does not implement the ``__delitem__`` method,
	so there is no way to trigger an :class:`.IObjectRemovedEvent`
	"""

	@Lazy
	def contentPackages(self):
		result = AbstractLibrary.contentPackages.fget(self)
		# Now fire the events letting listeners (e.g., index and question adders)
		# know that we have content. Randomize the order of this across worker
		# processes so that we don't collide too badly on downloading indexes if need be
		# (only matters if we are not preloading).
		# Do this in greenlets/parallel. This can radically speed up
		# S3 loading when we need the network.

		# TODO: If we are registering a library in a local site, via
		# z3c.baseregistry, does the IRegistrationEvent still occur
		# in the context of that site? I *think* so, need to prove it.
		# We need to be careful to keep the correct site, then, as we fire off
		# events in parallel
		titles = list(result)

		# NOTE that we immediately save the result of this
		# so that if an event handler wants to also enumerate content
		# packages we don't wind up notifying twice
		self.__dict__['contentPackages'] = result

		try:
			import gevent
		except ImportError: # pragma: no cover
			for title in titles:
				lifecycleevent.added( title )
		else:
			import random
			from zope.component.hooks import getSite, site
			random.seed()
			random.shuffle(titles)


			if False:
				# Enumerating in parallel greenlets
				# speeds up IO, but has issues reuising the
				# same connection to ZODB if it is ZEO
				title_greenlets = []
				current_site = getSite()

				def _notify_in_site( title ):
					# Need a level of functional redirection here
					# to workaround python's awkward closure rules
					with site(current_site):
						lifecycleevent.added( title )

				for title in titles:
					title_greenlets.append( gevent.spawn( _notify_in_site, title ) )

				gevent.joinall( title_greenlets, raise_error=True )
			else:
				for title in titles:
					lifecycleevent.added( title )

		return result

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
