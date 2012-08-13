#!/usr/bin/env python
"""
Objects for creating IContentLibrary objects based on the filesystem.
"""
from __future__ import print_function, unicode_literals

import os

from . import eclipse
from . import library

class StaticFilesystemLibrary(library.AbstractStaticLibrary):

	package_factory = staticmethod(eclipse.EclipseContentPackage)

	def __init__(self, paths=() ):
		"""
		Creates a library that will examine the given paths.

		:param paths: A sequence of strings pointing to directories to introspect for
			:class:`interfaces.IContentPackage` objects.
		EOD
		"""
		super(StaticFilesystemLibrary,self).__init__( paths=paths )


class DynamicFilesystemLibrary(library.AbstractLibrary):
	"""
	Implements a library by looking at the contents of a root
	directory, when needed.
	"""

	package_factory = staticmethod(eclipse.EclipseContentPackage)

	def __init__( self, root ):
		super(DynamicFilesystemLibrary,self).__init__()
		self._root = root

	@property
	def possible_content_packages(self):
		return [os.path.join( self._root, p) for p in os.listdir(self._root)
				if os.path.isdir( os.path.join( self._root, p ) )]

Library = StaticFilesystemLibrary
DynamicLibrary = DynamicFilesystemLibrary
from zope.deprecation import deprecated
deprecated( ['Library','DynamicLibrary'], "Prefer StaticFilesystemLibrary and DynamicFilesystemLibrary." )
