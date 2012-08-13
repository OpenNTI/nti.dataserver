#!/usr/bin/env python
"""
Generic implementations of IContentUnit functions
"""
from __future__ import print_function, unicode_literals
import os
import datetime
logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.deprecation import deprecate
from zope.cachedescriptors.property import Lazy

from nti.utils.property import alias

from nti.contentlibrary.interfaces import IContentUnit, IFilesystemContentUnit, IContentPackage, IFilesystemContentPackage
from nti.contentlibrary.interfaces import IDelimitedHierarchyContentUnit, IDelimitedHierarchyContentPackage

@interface.implementer(IContentUnit)
class ContentUnit(object):
	"""
	Simple implementation of :class:`IContentUnit`.
	"""

	ordinal = 1
	href = None
	ntiid = None
	icon = None

	# DCDescriptiveProperties
	title = None
	description = None


	children = ()
	__parent__ = None

	def __init__( self, **kwargs ):
		for k, v in kwargs.items():
			if hasattr( self, k ):
				setattr( self, k, v )

	def _get_name(self):
		return self.title
	def _set_name(self,n):
		self.title = n
	__name__ = property(_get_name,_set_name, None, "a synonym for title")
	label = __name__


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

	def read_contents_of_sibling_entry( self, sibling_name ):
		if self.filename:
			try:
				return open( os.path.join( os.path.dirname( self.filename ), sibling_name ), 'r' ).read()
			except (OSError,IOError):
				return None

	def does_sibling_entry_exist( self, sibling_name ):
		return os.path.exists( os.path.join( os.path.dirname( self.filename ), sibling_name ) )


@interface.implementer(IContentPackage)
class ContentPackage(ContentUnit):
	"""
	Simple implementation of :class:`IContentPackage`.
	"""

	root = None
	index = None
	index_last_modified = None
	installable = False
	archive = None
	renderVersion = 1

	# IDCExtended
	creators = ()
	subjects = ()
	contributors = ()
	publisher = ''

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

import rfc822
import time

@interface.implementer(IDelimitedHierarchyContentUnit)
class BotoS3ContentUnit(ContentUnit):
	"""

	.. py:attribute:: key
		The :class:`boto.s3.key.Key` for this unit.

	"""

	key = None

	@Lazy
	def lastModified( self ):
		result = rfc822.parsedate_tz( self.key.last_modified )
		if result is not None:
			result = rfc822.mktime_tz(result)
			# This is supposed to be coming in rfc822 format (see boto.s3.key)
			# But it doesn't always. So try to parse it ourself if we have to
		elif self.key.last_modified:
			# 2012-05-12T23:15:24.000Z
			result = datetime.datetime.strptime( self.key.last_modified, '%Y-%m-%dT%H:%M:%S.%fZ' )
			result = time.mktime( result )
		return result


	@Lazy
	def modified(self):
		return datetime.datetime.utcfromtimestamp( self.lastModified )

	created = modified

	def _sibling_key( self, sibling_name ):
		split = self.key.name.split( '/' )
		split[-1] = sibling_name
		new_key = type(self.key)( bucket=self.key.bucket, name='/'.join( split ) )
		return new_key


	def read_contents_of_sibling_entry( self, sibling_name ):
		if self.key:
			new_key =  self._sibling_key( sibling_name )
			return new_key.get_contents_as_string()

	def does_sibling_entry_exist( self, sibling_name ):
		return self.key.bucket.get_key( self._sibling_key( sibling_name ).name )


@interface.implementer(IDelimitedHierarchyContentPackage)
class BotoS3ContentPackage(ContentPackage,BotoS3ContentUnit):
	pass
