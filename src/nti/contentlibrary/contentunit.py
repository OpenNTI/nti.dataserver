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


@interface.implementer(IContentPackage)
class ContentPackage(ContentUnit):
	"""
	Simple implementation of :class:`IContentPackage`.
	"""

	root = None
	index = None
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

	index_last_modified = None

	@property
	@deprecate("Unclear what the replacement is yet.")
	def localPath( self ):
		if self.filename:
			return os.path.dirname( self.filename )


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
