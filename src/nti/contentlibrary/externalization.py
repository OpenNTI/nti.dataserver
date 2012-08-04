#!/usr/bin/env python
"""
Support for externalizing portions of the library.
"""
import urllib
import os

from zope import interface
from zope import component

from nti.externalization.externalization import toExternalObject, to_standard_external_dictionary
from nti.externalization.interfaces import IExternalObject, StandardExternalFields
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

@interface.implementer(IExternalObject)
@component.adapter(interfaces.IFilesystemContentPackage)
class _ContentPackageExternal(object):

	def __init__( self, package ):
		self.package = package

	def toExternalObject( self ):
		result = to_standard_external_dictionary( self.package )
		result.__name__ = self.package.__name__
		result.__parent__ = self.package.__parent__

		# TODO: We're making all kinds of assumptions about where in the
		# URL space these are
		def _o( p='' ):
			if p is None: return None
			if ' ' in p:
				# Generally, we don't want to quote the path portion: it should already
				# have been quoted with the TOC file was written. However, for
				# hand-edited TOCs, it is convenient if we do quote it.
				p = urllib.quote( p )
			return urllib.quote( '/' + os.path.basename( os.path.dirname(self.package.filename) ) ) + '/' + p
		result['icon'] = _o( self.package.icon )
		result['href'] = _o( self.package.href )

		result['root'] = _o()
		result['index'] = _o( os.path.basename( self.package.index ) ) if self.package.index else None
		result['title'] = self.package.title # Matches result['DCTitle']
		result['installable'] = self.package.installable
		result['version'] = '1.0' # This field was never defined. What does it mean?  I think we were thinking of generations
		result['renderVersion'] = self.package.renderVersion
		result[StandardExternalFields.NTIID] = self.package.ntiid

		if self.package.installable:
			result['archive'] = _o( self.package.archive ) # TODO: Assumptions
			result['Archive Last Modified'] = os.stat( os.path.join( os.path.dirname( self.package.filename ) ,self.package.archive ) )[os.path.stat.ST_MTIME]

		return result
