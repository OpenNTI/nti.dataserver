# -*- coding: utf-8 -*-
"""
Content types.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.dataserver import mimetype

from nti.utils.property import alias
from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as search_interfaces

@interface.implementer(search_interfaces.IWhooshBookContent)
class BookContent(SchemaConfigured):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshBookContent)

	intid = alias('docnum')
	last_modified = alias('lastModified')
	containerId = ContainerId = alias('ntiid')

@interface.implementer(search_interfaces.IWhooshVideoTranscriptContent)
class VideoTranscriptContent(SchemaConfigured):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshVideoTranscriptContent)

	last_modified = alias('lastModified')

@interface.implementer(search_interfaces.IWhooshNTICardContent)
class NTICardContent(SchemaConfigured):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshNTICardContent)
	
	content = alias('description')
	last_modified = alias('lastModified')
