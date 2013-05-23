#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements :mod:`nti.contentprocessing.metadata_extractors` related
functionality for items in the content library.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

from nti.ntiids.ntiids import find_object_with_ntiid
from nti.contentprocessing.metadata_extractors import ContentMetadata, ImageMetadata

@interface.implementer(cp_interfaces.IContentMetadataURLHandler)
class TagURLHandler(object):
	"""
	Registered as a URL handler for the NTIID URL scheme,
	``tag:``. If something is found, adapts it to :class:`IContentMetadata`.
	"""


	def __call__(self, url):
		obj = find_object_with_ntiid( url )
		if obj is not None:
			return cp_interfaces.IContentMetadata( obj, None )

@interface.implementer(cp_interfaces.IContentMetadata)
@component.adapter(lib_interfaces.IContentUnit)
def ContentMetadataFromContentUnit( content_unit ):
	# FIXME: The hrefs are probably wrong. We need to map
	# them at this level?
	result = ContentMetadata( title=content_unit.title,
							  description=content_unit.description,
							  contentLocation=content_unit.href,
							  mimeType='text/html' )
	result.__name__ = '@@metadata'
	result.__parent__ = content_unit # for ACL
	if content_unit.icon:
		image = ImageMetadata( url=content_unit.icon )
		image.__parent__ = result
		result.images = []
		result.images.append( image )
	return result
