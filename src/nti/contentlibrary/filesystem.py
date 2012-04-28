#!/usr/bin/env python
"""
Objects for creating IContentLibrary objects based on the filesystem.
"""
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

from zope import interface

import os
import xml.dom.minidom as minidom
import urllib
import string

from . import interfaces
from . import eclipse
from . import contentunit


class _AbstractLibrary(object):
	"""
	Base class for a Library. Subclasses must define the `paths` to inspect.

	:param paths: A sequence of strings pointing to directories to introspect for
		:class:`interfaces.IContentPackage` objects.
	"""

	interface.implements(interfaces.IContentPackageLibrary)

	paths = ()
	def __init__(self):
		pass

	@property
	def contentPackages(self):
		""" Returns a sequence of LibraryEntry items. """
		titles = []
		for pathEntry in self.paths:

			path = pathEntry
			# TODO: We need a factory or something here
			title = eclipse.EclipseContentPackage( path )
			if title:
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


	def pathToNTIID(self, ntiid):
		""" Returns a list of TOCEntry objects in order until
		the given ntiid is encountered, or None of the id cannot be found."""
		for title in self.titles:
			result = contentunit.pathToPropertyValue( title, 'ntiid', ntiid )
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


class Library(_AbstractLibrary):

	def __init__(self, paths=() ):
		"""
		Creates a library that will examine the given paths.

		:param paths: A sequence of strings pointing to directories to introspect for
			:class:`interfaces.IContentPackage` objects.
		EOD
		"""
		super(Library,self).__init__()
		self.paths = paths

class DynamicLibrary(_AbstractLibrary):
	"""
	Implements a library by looking at the contents of a root
	directory, when needed.
	"""

	def __init__( self, root ):
		super(DynamicLibrary,self).__init__()
		self._root = root

	@property
	def paths(self):
		return [os.path.join( self._root, p) for p in os.listdir(self._root)
				if os.path.isdir( os.path.join( self._root, p ) )]
