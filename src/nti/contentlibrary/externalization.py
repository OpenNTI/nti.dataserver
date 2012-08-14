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

@interface.implementer(IExternalObject)
@component.adapter(interfaces.IContentPackageLibrary)
class _ContentPackageLibraryExternal(object):
	def __init__( self, library ):
		self.library = library

	def toExternalObject( self ):
		return {
				 'title': "Library",
				 'titles' : [toExternalObject(x) for x in self.library.titles] }

def _path_join( package, path='' ):
	if path is None:
		return None
	if ' ' in path:
		# Generally, we don't want to quote the path portion: it should already
		# have been quoted with the TOC file was written. However, for
		# hand-edited TOCs, it is convenient if we do quote it.
		path = urllib.quote( path )
	return urllib.quote( '/' + os.path.basename( os.path.dirname( package.filename ) ) ) + '/' + path

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
			return _path_join( self.package, path=p )
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

from pyramid import traversal

@component.adapter(interfaces.IFilesystemContentUnit)
@interface.implementer(interfaces.IContentUnitHrefMapper)
class _FilesystemContentUnitHrefMapper(object):
	href = None

 	def __init__( self, unit ):
		root_package = traversal.find_interface( unit, interfaces.IContentPackage )
		href = _path_join( root_package, unit.href )
		href = href.replace( '//', '/' )
		if not href.startswith( '/' ):
			href = '/' + href
		self.href = href


from urlparse import urljoin

@interface.implementer(IExternalObject)
@component.adapter(interfaces.IS3ContentPackage)
class _S3ContentPackageExternal(object):

	def __init__( self, package ):
		self.package = package

	def toExternalObject( self ):
		result = to_standard_external_dictionary( self.package )
		result.__name__ = self.package.__name__
		result.__parent__ = self.package.__parent__

		# We assume that these are in URL space according to the
		# bucket name
		root_url = 'http://' + self.package.key.bucket.name + '/' + self.package.get_parent_key().key + '/'

		result['icon'] = urljoin( root_url, self.package.icon ) # TODO: For some reason these are relative paths
		result['href'] = urljoin( root_url, self.package.href ) # ...

		result['root'] = root_url
		result['index'] = 'http://' + self.package.key.bucket.name + '/' + self.package.index.key # But this is a key
		result['title'] = self.package.title # Matches result['DCTitle']
		result['installable'] = self.package.installable
		result['version'] = '1.0' # This field was never defined. What does it mean?  I think we were thinking of generations
		result['renderVersion'] = self.package.renderVersion
		result[StandardExternalFields.NTIID] = self.package.ntiid

		if self.package.installable:
			result['archive'] = urljoin( root_url, self.package.archive )
			result['Archive Last Modified'] = self.package.archive_unit.lastModified

		return result

@component.adapter(interfaces.IS3ContentUnit)
@interface.implementer(interfaces.IContentUnitHrefMapper)
class _S3ContentUnitHrefMapper(object):
	href = None

 	def __init__( self, unit ):
		self.href = 'http://' + unit.key.bucket.name + '/' + unit.key.key
