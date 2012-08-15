#!/usr/bin/env python
"""
Support for externalizing portions of the library.
"""
import urllib
from urlparse import urljoin
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

def _path_join( root_url, path='' ):
	if path is None:
		return None
	if ' ' in path:
		# Generally, we don't want to quote the path portion: it should already
		# have been quoted with the TOC file was written. However, for
		# hand-edited TOCs, it is convenient if we do quote it.
		path = urllib.quote( path )

	return urljoin( root_url, path )

def _root_url_of_unit( unit ):
	mapper = interfaces.IContentUnitHrefMapper( unit.get_parent_key(), None )
	if mapper:
		href = mapper.href
	else:
		href = '/' + unit.get_parent_key()
	return href + ('' if href.endswith( '/' ) else '/')  # trailing slash is important for urljoin

@interface.implementer(IExternalObject)
class _ContentPackageExternal(object):

	def __init__( self, package ):
		self.package = package

	def toExternalObject( self ):
		result = to_standard_external_dictionary( self.package )
		result.__name__ = self.package.__name__
		result.__parent__ = self.package.__parent__

		root_url = _root_url_of_unit( self.package )
		result._root_url = root_url

		result['icon'] = _path_join( root_url, self.package.icon ) # TODO: For some reason these are relative paths
		result['href'] = _path_join( root_url, self.package.href ) # ...

		result['root'] = root_url
		#result['index'] = _path_join( root_url, os.path.basename( self.package.index ) if self.package.index else None )
		result['title'] = self.package.title # Matches result['DCTitle']

		result['version'] = '1.0' # This field was never defined. What does it mean?  I think we were thinking of generations
		result['renderVersion'] = self.package.renderVersion
		result[StandardExternalFields.NTIID] = self.package.ntiid

		if self.package.installable:
			result['archive'] = interfaces.IContentUnitHrefMapper( self.package.archive_unit ).href
			result['Archive Last Modified'] = self.package.archive_unit.lastModified

		return result


@interface.implementer(IExternalObject)
@component.adapter(interfaces.IFilesystemContentPackage)
class _FilesystemContentPackageExternal(_ContentPackageExternal):

	def toExternalObject( self ):
		result = super(_FilesystemContentPackageExternal,self).toExternalObject()
		# TODO: Index handling is ugly
		result['index'] = _path_join( result._root_url, os.path.basename( self.package.index ) if self.package.index else None )
		return result

from pyramid import traversal

@component.adapter(interfaces.IFilesystemContentUnit)
@interface.implementer(interfaces.IContentUnitHrefMapper)
class _FilesystemContentUnitHrefMapper(object):
	href = None

 	def __init__( self, unit ):
		root_package = traversal.find_interface( unit, interfaces.IContentPackage )
		root_url = _root_url_of_unit( root_package )
		__traceback_info__ = unit, root_package, root_url
		href = _path_join( root_url, unit.href )
		href = href.replace( '//', '/' )
		if not href.startswith( '/' ):
			href = '/' + href
		self.href = href

@interface.implementer(IExternalObject)
@component.adapter(interfaces.IS3ContentPackage)
class _S3ContentPackageExternal(_ContentPackageExternal):


	def toExternalObject( self ):
		result = super(_S3ContentPackageExternal,self).toExternalObject()
		# TODO: For some reason self.package.icon and self.package.href are relative paths,
		# but self.package.index is a full key
		result['index'] = interfaces.IContentUnitHrefMapper( self.package.index ).href
		return result

@component.adapter(interfaces.IS3ContentUnit)
@interface.implementer(interfaces.IAbsoluteContentUnitHrefMapper)
class _S3ContentUnitHrefMapper(object):
	href = None

 	def __init__( self, unit ):
		self.href = interfaces.IContentUnitHrefMapper( unit.key ).href

@component.adapter(interfaces.IS3Key)
@interface.implementer(interfaces.IAbsoluteContentUnitHrefMapper)
class _S3KeyHrefMapper(object):
	"""
	Produces HTTP URLs for keys in buckets.
	"""
	href = None

 	def __init__( self, key ):
		# We have to force HTTP here, because using https (or protocol relative)
		# falls down for the browser: the certs on the CNAME we redirect to, *.s3.aws.amazon.com
		# don't match for bucket.name host
		self.href = 'http://' + key.bucket.name + '/' + key.key
