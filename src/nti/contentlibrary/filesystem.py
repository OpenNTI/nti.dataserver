#!/usr/bin/env python
"""
Objects for creating IContentLibrary objects based on the filesystem.
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

import os
from os.path import join as path_join
import datetime

from zope import interface
from zope.deprecation import deprecate
from zope.cachedescriptors.property import Lazy

from nti.utils.property import alias

from . import eclipse
from . import library

from .contentunit import ContentUnit
from .contentunit import ContentPackage
from .interfaces import IFilesystemContentUnit
from .interfaces import IFilesystemContentPackage

def _TOCPath( path ):
	return os.path.abspath( path_join( path, eclipse.TOC_FILENAME ))

def _hasTOC( path ):
	""" Does the given path point to a directory containing a TOC file?"""
	return os.path.exists( _TOCPath( path ) )

def _isTOC( path ):
	return os.path.basename( path ) == eclipse.TOC_FILENAME


def _package_factory( localPath ):
	if _isTOC( localPath ):
		localPath = os.path.dirname( localPath )

	if not _hasTOC( localPath ):
		return None

	localPath = os.path.abspath( localPath )
	toc_path = _TOCPath( localPath )
	temp_entry = FilesystemContentUnit( filename=toc_path )
	return eclipse.EclipseContentPackage( temp_entry, FilesystemContentPackage, FilesystemContentUnit )

class StaticFilesystemLibrary(library.AbstractStaticLibrary):

	package_factory = staticmethod(_package_factory)

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
	package_factory = staticmethod(_package_factory)

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


@interface.implementer(IFilesystemContentUnit)
class FilesystemContentUnit(ContentUnit):
	"""
	Adds the `filename` property, an alias of the `key` property
	"""

	filename = None
	key = alias('filename')

	@Lazy
	def lastModified( self ):
		try:
			return os.stat( self.filename )[os.path.stat.ST_MTIME]
		except OSError:
			logger.debug( "Failed to get last modified for %s", self.filename, exc_info=True )
			return 0

	@Lazy
	def modified(self):
		return datetime.datetime.utcfromtimestamp( self.lastModified )

	@Lazy
	def created(self):
		try:
			return datetime.datetime.utcfromtimestamp( os.stat( self.filename )[os.path.stat.ST_CTIME] )
		except OSError:
			logger.debug( "Failed to get created for %s", self.filename, exc_info=True )
			return datetime.datetime.utcfromtimestamp( 0 )

	def read_contents(self):
		try:
			return open( self.filename, 'r' ).read()
		except IOError:
			return None

	def make_sibling_key( self, sibling_name ):
		return os.path.join( os.path.dirname( self.filename ), sibling_name )

	def read_contents_of_sibling_entry( self, sibling_name ):
		if self.filename:
			try:
				return open( self.make_sibling_key( sibling_name ), 'r' ).read()
			except (OSError,IOError):
				return None

	def does_sibling_entry_exist( self, sibling_name ):
		return os.path.exists( self.make_sibling_key( sibling_name  ) )

@interface.implementer(IFilesystemContentPackage)
class FilesystemContentPackage(ContentPackage,FilesystemContentUnit):
	"""
	Adds the `filename` property to the ContentPackage.
	"""

	@property
	@deprecate("Unclear what the replacement is yet.")
	def localPath( self ):
		if self.filename:
			return os.path.dirname( self.filename )
