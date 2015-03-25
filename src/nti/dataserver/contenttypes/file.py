#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.file.upload import nameFinder

from zope.location.interfaces import IContained

from plone.namedfile.file import NamedBlobFile

from nti.dataserver.core.schema import DataURI
from nti.dataserver.core.interfaces import ILinkExternalHrefOnly

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.externalization import to_external_object
from nti.externalization.externalization import to_external_ntiid_oid
from nti.externalization.datastructures import AbstractDynamicObjectIO

from nti.links.links import Link

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from ..interfaces import INamedFile
from ..interfaces import IInternalFileRef

OID = StandardExternalFields.OID
NTIID = StandardExternalFields.NTIID

@interface.implementer(INamedFile, IContained)
class NamedFile(PersistentCreatedModDateTrackingObject, # Order matters
				NamedBlobFile,
				SchemaConfigured):

	createDirectFieldProperties(INamedFile)
		
	name = None
	__parent__ = __name__ = None

	mime_type = mimeType = 'application/vnd.nextthought.namedfile'
	
	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
		PersistentCreatedModDateTrackingObject.__init__(self, *args, **kwargs)
		
	def __str__(self):
		return "%s(%s)" % (self.__class__.__name__, self.filename)
	__repr__ = __str__

@component.adapter(INamedFile)
class _NamedFileObjectIO(AbstractDynamicObjectIO):

	def __init__( self, ext_self ):
		super(_NamedFileObjectIO,self).__init__()
		self._ext_self = ext_self

	def _ext_replacement(self):
		return self._ext_self

	def _ext_all_possible_keys(self):
		return ()

	# For symmetry with the other response types,
	# we accept either 'url' or 'value'

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		ext_self = self._ext_replacement()
		if parsed.get('download_url') or parsed.get(OID) or parsed.get(NTIID):
			## when updating from an external source and either download_url or 
			## NTIID/OID is provided save the reference
			interface.alsoProvides(ext_self, IInternalFileRef)
			ext_self.reference = parsed.get(OID) or parsed.get(NTIID)
			# then remove those fields to avoid any hint of a copy
			for name in (OID, NTIID, 'download_url', 'url', 'value', 'filename'):
				parsed.pop(name, None)
		# start update
		updated = super(_NamedFileObjectIO, self).updateFromExternalObject(parsed, *args, **kwargs)
		
		# file data
		ext_self = self._ext_replacement()
		url = parsed.get('url') or parsed.get('value')
		name = parsed.get('name') or parsed.get('Name')
		if url:
			data_url = DataURI(__name__='url').fromUnicode( url )
			ext_self.contentType = data_url.mimeType
			ext_self.data = data_url.data
			updated = True
			
		# file data
		if 'filename' in parsed:
			ext_self.filename = parsed['filename']
			# some times we get full paths
			name_found = nameFinder( ext_self )
			if name_found:
				ext_self.filename = name_found
			name = ext_self.filename if not name else name
			updated = True
			
		# contentType
		for name in ('FileMimeType', 'contentType', 'type'):
			if name in parsed:
				ext_self.contentType = bytes(parsed[name])
				updated = True
				break
	
		# file id
		if name is not None:
			ext_self.name = name
		return updated

	def toExternalObject( self, mergeFrom=None, **kwargs ):
		ext_dict = super(_NamedFileObjectIO,self).toExternalObject(**kwargs)
		the_file = self._ext_replacement()
		ext_dict['name'] = the_file.name or None
		ext_dict['filename'] = the_file.filename or None
		ext_dict['FileMimeType'] = the_file.mimeType or None
		ext_dict['MimeType'] = 'application/vnd.nextthought.namedfile'
		target = to_external_ntiid_oid(the_file, add_to_connection=True)
		if target:
			for element, key in ('view','url'), ('download','download_url'):
				link = Link( target=target,
							 target_mime_type=the_file.contentType,
							 elements=(element,),
							 rel="data" )
				interface.alsoProvides( link, ILinkExternalHrefOnly )
				ext_dict[key] = to_external_object( link )
		else:
			ext_dict['url'] = None
			ext_dict['download_url'] = None
		ext_dict['value'] = ext_dict['url']
		return ext_dict

def _NamedFileFactory(ext_obj):
	factory = NamedFile
	return factory
