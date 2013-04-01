#!/usr/bin/env python
"""
Objects for creating IContentLibrary objects based on the filesystem.
"""
from __future__ import print_function, unicode_literals, absolute_import

logger = __import__('logging').getLogger(__name__)

import os
from os.path import join as path_join
import datetime

from zope import interface
from zope.cachedescriptors.property import Lazy, readproperty
from zope.location.interfaces import IContained as IZContained

import repoze.lru
from nti.utils.property import alias, CachedProperty

from . import eclipse
from . import library

from .contentunit import ContentUnit
from .contentunit import ContentPackage
from .interfaces import IFilesystemContentUnit
from .interfaces import IFilesystemContentPackage
from .interfaces import IFilesystemKey
from .interfaces import IFilesystemBucket

def _TOCPath( path ):
	return os.path.abspath( path_join( path, eclipse.TOC_FILENAME ))

def _hasTOC( path ):
	""" Does the given path point to a directory containing a TOC file?"""
	return os.path.exists( _TOCPath( path ) )

def _isTOC( path ):
	return os.path.basename( path ) == eclipse.TOC_FILENAME


def _package_factory( directory ):
	if not _hasTOC( directory ):
		return None

	directory = os.path.abspath( directory )
	#toc_path = _TOCPath( directory )
	bucket = FilesystemBucket( directory )
	key = FilesystemKey( bucket=bucket, name=eclipse.TOC_FILENAME )
	temp_entry = FilesystemContentUnit( key=key )
	assert key.absolute_path == _TOCPath( directory ) == temp_entry.filename
	package = eclipse.EclipseContentPackage( temp_entry, FilesystemContentPackage, FilesystemContentUnit )
	__traceback_info__ = directory, bucket, key, temp_entry, package
	assert package.key.bucket == bucket
	bucket.__parent__ = package
	return package

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


# TODO: The DynamicFilesystemLibrary should be made to work
# with the `watchdog` library for noticing changes.
# watchdog uses inotify on linux and fsevents/kqueue on OS X,
# our two supported platforms. I (JAM) think the only trick might be
# getting it to work with gevent?

class DynamicFilesystemLibrary(library.AbstractLibrary):
	"""
	Implements a library by looking at the contents of a root
	directory, everytime needed.
	"""

	package_factory = staticmethod(_package_factory)

	def __init__( self, root ):
		super(DynamicFilesystemLibrary,self).__init__()
		self._root = root

	def _query_possible_content_packages(self):
		return [os.path.join( self._root, p)
				for p in os.listdir(self._root)
				if os.path.isdir( os.path.join( self._root, p ) )]
	possible_content_packages = property(_query_possible_content_packages)

	@readproperty
	def _root_mtime(self):
		return os.stat( self._root )[os.path.stat.ST_MTIME]

	@property
	def lastModified(self):
		return max(self._root_mtime, super(DynamicFilesystemLibrary,self).lastModified)

class EnumerateOnceFilesystemLibrary(DynamicFilesystemLibrary):
	"""
	A library that will examine the to find possible content packages
	only the very first time that it is requested to. Changes after that
	point will be ignored.
	"""

	@CachedProperty
	def possible_content_packages(self):
		return tuple( self._query_possible_content_packages() )

	_root_mtime = Lazy(DynamicFilesystemLibrary._root_mtime.func)


@interface.implementer(IFilesystemBucket,IZContained)
class FilesystemBucket(object):
	__slots__ = ('name','__parent__')

	__name__ = alias('name')
	key = alias('name')

	def __init__( self, name=None, parent=None ):
		self.name = name
		self.__parent__ = parent

	def __eq__(self, other):
		return self.name == other.name

	def __hash__(self):
		return hash(self.name)

@interface.implementer(IFilesystemKey,IZContained)
class FilesystemKey(object):
	#__slots__ = ('name', 'bucket') # Doesn't play well with CachedProperty

	bucket = None
	name = None

	__name__ = alias('name')
	key = alias('name')
	__parent__ = alias('bucket')


	def __init__( self, bucket=None, name=None ):
		if bucket is not None:
			self.bucket = bucket
		if name is not None:
			self.name = name

	@CachedProperty( 'bucket', 'name' )
	def absolute_path( self ):
		return os.path.join( self.bucket.name, self.name ) if self.bucket and self.bucket.name else self.name

	def __eq__( self, other ):
		try:
			return self.bucket == other.bucket and self.name == other.name
		except AttributeError:
			return NotImplemented

	def __repr__( self ):
		return "<FilesystemKey '%s'>" % self.absolute_path

	def __hash__( self ):
		return hash(self.absolute_path)

from .contentunit import _exist_cache
from .contentunit import _content_cache

@interface.implementer(IFilesystemContentUnit)
class FilesystemContentUnit(ContentUnit):
	"""
	Adds the `filename` property, an alias of the `key` property
	"""

	def _get_key(self):
		return self.__dict__.get('key', None)
	def _set_key( self, nk ):
		if isinstance( nk, basestring ):
			# OK, the key is a simple string, meaning a path within
			# a directory.
			# TODO: Assuming one level of hierarchy
			bucket_name = os.path.dirname( nk )
			key_name = os.path.basename( nk )
			bucket = FilesystemBucket( bucket_name ) if bucket_name else None
			if bucket:
				bucket.__parent__ = self
			file_key = FilesystemKey( bucket=bucket, name=key_name )
			self.__dict__['key'] = file_key
		else:
			self.__dict__['key'] = nk
	key = property(_get_key, _set_key)


	def _get_filename(self):
		return self.key.absolute_path if self.key else None
	filename = property(_get_filename, _set_key )

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

	@repoze.lru.lru_cache( None, cache=_content_cache )
	def read_contents(self):
		try:
			return open( self.filename, 'r' ).read()
		except IOError:
			return None

	def get_parent_key( self ):
		return FilesystemKey( bucket=self.key.bucket, name='' )

	def make_sibling_key( self, sibling_name ):
		__traceback_info__ = self.filename, sibling_name
		key = FilesystemKey( bucket=self.key.bucket, name=sibling_name )
		assert key.absolute_path == os.path.join( os.path.dirname( self.filename ), sibling_name )
		return key
		#return os.path.join( os.path.dirname( self.filename ), sibling_name )

	@repoze.lru.lru_cache( None, cache=_content_cache ) # first arg is ignored. This caches with the key (self, sibling_name)
	def _do_read_contents_of_sibling_entry( self, sibling_name ):
		try:
			with open( self.make_sibling_key( sibling_name ).absolute_path, 'r' ) as f:
				return f.read()
		except (OSError,IOError):
			return None

	def read_contents_of_sibling_entry( self, sibling_name ):
		if self.filename:
			return self._do_read_contents_of_sibling_entry( sibling_name )

	@repoze.lru.lru_cache( None, cache=_exist_cache )
	def does_sibling_entry_exist( self, sibling_name ):
		sib_key = self.make_sibling_key( sibling_name )
		return sib_key if os.path.exists( sib_key.absolute_path ) else None

	def __repr__( self ):
		return "<%s.%s '%s' '%s'>" % (self.__class__.__module__, self.__class__.__name__,
									  self.__name__, self.filename )


	def __eq__( self, other ):
		try:
			return self.key == other.key and self.__parent__ == other.__parent__
		except AttributeError:
			return NotImplemented

	def __hash__( self ):
		return hash(self.filename)

@interface.implementer(IFilesystemContentPackage)
class FilesystemContentPackage(ContentPackage,FilesystemContentUnit):
	"""
	Adds the `filename` property to the ContentPackage.
	"""

	TRANSIENT_EXCEPTIONS = (IOError,)
