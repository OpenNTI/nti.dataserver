#!/usr/bin/env python
"""
Generic implementations of IContentUnit functions
"""
from __future__ import print_function, unicode_literals
import os
import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope.deprecation import deprecate


from nti.contentlibrary.interfaces import IContentUnit, IFilesystemContentUnit, IContentPackage, IFilesystemContentPackage


class ContentUnit(object):
	"""
	Simple implementation of :class:IContentUnit.
	"""
	interface.implements(IContentUnit)

	ordinal = 1
	href = None
	ntiid = None
	title = None
	icon = None

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



class FilesystemContentUnit(ContentUnit):
	"""
	Adds the 'filename' property.
	"""
	interface.implements(IFilesystemContentUnit)

	filename = None

class ContentPackage(ContentUnit):
	"""
	Simple implementation of :class:`IContentPackage`.
	"""
	interface.implements(IContentPackage)
	root = None
	index = None
	installable = False
	archive = None

class FilesystemContentPackage(ContentPackage,FilesystemContentUnit):
	"""
	Adds the `filename` property to the ContentPackage.
	"""
	interface.implements(IFilesystemContentPackage)

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
