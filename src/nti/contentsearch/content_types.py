# -*- coding: utf-8 -*-
"""
Content types.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.container import contained as zcontained

from nti.dataserver import mimetype

from nti.externalization.externalization import make_repr

from nti.utils.property import alias
from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as search_interfaces

@interface.implementer(search_interfaces.IWhooshBookContent)
class BookContent(SchemaConfigured, zcontained.Contained):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshBookContent)

	intid = alias('docnum')
	last_modified = alias('lastModified')
	containerId = ContainerId = alias('ntiid')

	__repr__ = make_repr()

@interface.implementer(search_interfaces.IWhooshVideoTranscriptContent)
class VideoTranscriptContent(SchemaConfigured, zcontained.Contained):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshVideoTranscriptContent)

	last_modified = alias('lastModified')

	__repr__ = make_repr()

@interface.implementer(search_interfaces.IWhooshNTICardContent)
class NTICardContent(SchemaConfigured, zcontained.Contained):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshNTICardContent)
	
	content = alias('description')
	last_modified = alias('lastModified')

	__repr__ = make_repr()

