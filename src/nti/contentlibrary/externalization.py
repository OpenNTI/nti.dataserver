#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for externalizing portions of the library.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from urlparse import urljoin
import anyjson as json
import collections
import os
import six
import urllib

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
	href = interfaces.IContentUnitHrefMapper( unit.get_parent_key() ).href
	return href + ('' if href.endswith( '/' ) else '/')  # trailing slash is important for urljoin

#: This file, if present, will be read to gain a dictionary
#: of presentation properties to be attached to the external
#: representation of a content package (in the ``PresentationProperties`` key).
#: We take little interest in the keys and values found here,
#: simply requiring the keys to be strings; however, we do
#: list some well-known keys and their corresponding values
#: (when a dot is used, it means the key nested inside the containing dictionary):
#:
#: ``numbering``
#:		 A dictionary that controls the presentation of "chapter numbers" and "section numbers"
#: ``numbering.suppressed``
#:		A boolean; if `True`, then the user interface should not attempt to
#:		add and display automatic numbering information (default is False, and the UI should display
#:		automatic numbering).
#: ``numbering.type``
#:		A one character string as in HTML (1, a, A, i, I) giving the type of marker to use
#:		for automatic numbering (for decimal numbers, lowercase alphabetic, uppercase alphabetic,
#:		and lower and upper Roman, respectively); the default is 1
#: ``numbering.start``
#:		An integer giving the starting number; defaults to 1.
#: ``numbering.separator``
#:		A string giving the value to put between levels in the tree when autonumbering
#:		a complete path. Defaults to '.'
#:
DEFAULT_PRESENTATION_PROPERTIES_FILE = 'nti_default_presentation_properties.json'

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
		result['title'] = self.package.title # Matches result['DCTitle']

		result['index'] = interfaces.IContentUnitHrefMapper( self.package.index ).href if self.package.index else None
		result['index_jsonp'] = interfaces.IContentUnitHrefMapper( self.package.index_jsonp ).href if self.package.index_jsonp else None


		result['version'] = '1.0' # This field was never defined. What does it mean?  I think we were thinking of generations
		result['renderVersion'] = self.package.renderVersion
		result[StandardExternalFields.NTIID] = self.package.ntiid

		result['installable'] = self.package.installable
		if self.package.installable:
			result['archive'] = interfaces.IContentUnitHrefMapper( self.package.archive_unit ).href
			result['Archive Last Modified'] = self.package.archive_unit.lastModified


		# Attach presentation properties. This is here for several reasons:
		# - This information is not normative, not used by the server,
		#    and thus not part of the IContentPackage interface;
		# - We are moving toward having IContentPackages be dynamic and constructed
		#   from sub-parts of other IContentPackages; if this were a static part of the IContentPackage,
		#   extracted from eclipse-toc.xml, such information would get lost when nodes are used
		#   outside their original context;
		# - We can imagine supplying different presentation information to different clients;
		#   this is easy to do by registering decorators for (IContentPackage,IRequest)

		presentation_properties_cache_name = '_v_presentation_properties'
		presentation_properties = getattr( self.package, presentation_properties_cache_name, None )
		if presentation_properties is None:
			presentation_properties = {}
			try:
				ext_data = self.package.read_contents_of_sibling_entry( DEFAULT_PRESENTATION_PROPERTIES_FILE )
			except self.package.TRANSIENT_EXCEPTIONS:
				ext_data = None
				presentation_properties = None # So we retry next time
			if ext_data:
				presentation_properties = json.loads( ext_data )
				assert isinstance(presentation_properties, collections.Mapping)
				for k in presentation_properties:
					assert isinstance(k,six.string_types)

			setattr( self.package, presentation_properties_cache_name, presentation_properties )

		result['PresentationProperties'] = presentation_properties
		return result


@interface.implementer(IExternalObject)
@component.adapter(interfaces.IFilesystemContentPackage)
class _FilesystemContentPackageExternal(_ContentPackageExternal):
	pass


from pyramid import traversal

@component.adapter(interfaces.IFilesystemContentUnit)
@interface.implementer(interfaces.IContentUnitHrefMapper)
class _FilesystemContentUnitHrefMapper(object):
	href = None

	def __init__(self, unit):
		self.href = interfaces.IContentUnitHrefMapper( unit.key ).href

@component.adapter(interfaces.IFilesystemKey)
@interface.implementer(interfaces.IContentUnitHrefMapper)
class _FilesystemKeyHrefMapper(object):
	href = None

	def __init__(self, key):
		root_package = traversal.find_interface( key, interfaces.IContentPackage )
		root_url = '/' + os.path.basename( root_package.dirname ) + '/'
		__traceback_info__ = key, root_package, root_url
		href = _path_join( root_url, key.key )

		library = traversal.find_interface( key, interfaces.IContentPackageLibrary )
		prefix = getattr( library, 'url_prefix', '' )
		# We require that prefix be a valid segment, ending in a '/', or empty
		href = prefix + href

		href = href.replace( '//', '/' )
		if not href.startswith( '/' ):
			href = '/' + href
		self.href = href


@interface.implementer(IExternalObject)
@component.adapter(interfaces.IS3ContentPackage)
class _S3ContentPackageExternal(_ContentPackageExternal):
	pass


@component.adapter(interfaces.IS3ContentUnit)
@interface.implementer(interfaces.IAbsoluteContentUnitHrefMapper)
class _S3ContentUnitHrefMapper(object):
	href = None

	def __init__(self, unit):
		self.href = interfaces.IContentUnitHrefMapper( unit.key ).href

@component.adapter(interfaces.IS3Key)
@interface.implementer(interfaces.IAbsoluteContentUnitHrefMapper)
class _S3KeyHrefMapper(object):
	"""
	Produces HTTP URLs for keys in buckets.
	"""
	href = None

	def __init__(self, key):
		# We have to force HTTP here, because using https (or protocol relative)
		# falls down for the browser: the certs on the CNAME we redirect to, *.s3.aws.amazon.com
		# don't match for bucket.name host
		self.href = 'http://' + key.bucket.name + '/' + key.key

@interface.implementer(interfaces.IAbsoluteContentUnitHrefMapper)
class CDNS3KeyHrefMapper(object):
	"""
	Produces protocol-relative URLs for keys in S3 buckets.

	Use this mapper when the content in a bucket is configured to be accessible
	at a specific address, typically in a CDN distribution. This mapper returns
	protocol relative addresses because the CDN address is assumed to be
	its own CNAME and equipped with certificates.
	"""
	href = None

	def __init__(self, key, cdn_cname):
		"""
		:param string cdn_name: The FQDN where the request should be directed.
		"""
		self.href = '//' + cdn_cname + '/' + key.key

class CDNS3KeyHrefMapperFactory(object):
	"""
	A factory to produce :class:`CDNS3KeyHrefMapper` objects. Register
	this object (usually in code) as an adapter for S3 content objects,
	knowing the given name of the CDN distribution.
	"""

	def __init__( self, cdn_name ):
		self.cdn_name = cdn_name

	def __call__( self, key ):
		return CDNS3KeyHrefMapper( key, self.cdn_name )

def map_all_buckets_to( cdn_name, _global=True ):
	"""
	WARNING: This API has global effects. Use
	with extreme caution.
	"""
	if _global:
		site_man = component.getGlobalSiteManager()
	else:
		site_man = component.getSiteManager()

	# manually clear any previous registration
	site_man.unregisterAdapter( required=(interfaces.IS3Key,),
								provided=interfaces.IAbsoluteContentUnitHrefMapper )
	# Note that we only need to register for the key, as the IS3ContentUnit mapper
	# simply maps the unit's key
	site_man.registerAdapter( CDNS3KeyHrefMapperFactory( cdn_name ),
							  required=(interfaces.IS3Key,),
							  provided=interfaces.IAbsoluteContentUnitHrefMapper )
