#!/usr/bin/env python
"""
Classes useful for working with libraries.
"""
from __future__ import print_function, unicode_literals

from zope import interface

from . import interfaces
from . import contentunit


@interface.implementer(interfaces.IContentPackageLibrary)
class AbstractLibrary(object):
	"""
	Base class for a Library. Subclasses must define the `paths` to inspect.

	.. py:attribute:: possible_content_packages
		A sequence of objects to introspect for :class:`interfaces.IContentPackage` objects.
	"""

	package_factory = None
	possible_content_packages = ()

	def __init__(self):
		pass

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

	def __getitem__( self, key ):
		"""
		:return: The LibraryEntry having a name or ntiid that matches `key`.
		"""
		for title in self.titles:
			if key in (title.title, title.ntiid):
				return title
		raise KeyError( key )

	def get( self, key, default=None ):
		try:
			return self[key]
		except KeyError:
			return default

	def pathToNTIID(self, ntiid):
		""" Returns a list of TOCEntry objects in order until
		the given ntiid is encountered, or None of the id cannot be found."""
		for title in self.titles:
			result = pathToPropertyValue( title, 'ntiid', ntiid )
			if result:
				return result
		return None

	def childrenOfNTIID( self, ntiid ):
		""" Returns a flattened list of all the children entries of ntiid
		in no particular order. If there are no children, returns []"""
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


class AbstractStaticLibrary(AbstractLibrary):

	def __init__(self, paths=() ):
		"""
		Creates a library that will examine the given paths.

		:param paths: A sequence of strings pointing to directories to introspect for
			:class:`interfaces.IContentPackage` objects.

		"""
		super(AbstractStaticLibrary,self).__init__()
		self.possible_content_packages = paths

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
