#!/usr/bin/env python
"""
Support for externalizing portions of the library.
"""
import urllib
import os

from zope import interface
from zope import component

from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import IExternalObject
from nti.contentlibrary import interfaces

class _ContentPackageLibraryExternal(object):
	interface.implements(IExternalObject)
	component.adapts(interfaces.IContentPackageLibrary)

	def __init__( self, library ):
		self.library = library

	def toExternalObject( self ):
		return {
				 'title': "Library",
				 'titles' : [toExternalObject(x) for x in self.library.titles] }

class _ContentPackageExternal(object):
	interface.implements(IExternalObject)
	component.adapts(interfaces.IFilesystemContentPackage)

	def __init__( self, package ):
		self.package = package

	def toExternalObject( self ):
		result = LocatedExternalDict()
		result.__name__ = self.package.__name__
		result.__parent__ = self.package.__parent__
		# TODO: We're making all kinds of assumptions about where in the
		# URL space these are
		def _o( p='' ):
			return urllib.quote( '/' + os.path.basename( os.path.dirname(self.package.filename) ) + '/' + p )
		result['icon'] = _o( self.package.icon )
		result['href'] = _o( self.package.href )

		result['root'] = _o()
		result['index'] = _o( os.path.basename( self.package.index ) )
		result['title'] = self.package.title
		result['installable'] = self.package.installable
		result['version'] = '1.0'

		if self.package.installable:
			result['archive'] = _o( self.package.archive ) # TODO: Assumptions
			result['Archive Last Modified'] = os.stat( os.path.join( os.path.dirname( self.package.filename ) ,self.package.archive ) )[os.path.stat.ST_MTIME]

		return result
