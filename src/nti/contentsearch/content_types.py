#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content types.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.container import contained as zcontained

from nti.externalization.externalization import make_repr

from nti.mimetype import mimetype

from nti.utils.property import alias
from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from . import interfaces as search_interfaces

class _DocNumMixin(zcontained.Contained):

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return self is other or self.docnum == other.docnum
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.docnum)
		return xhash

@interface.implementer(search_interfaces.IWhooshBookContent)
class BookContent(SchemaConfigured, _DocNumMixin):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshBookContent)

	intid = alias('docnum')
	last_modified = alias('lastModified')
	containerId = ContainerId = alias('ntiid')

@interface.implementer(search_interfaces.IWhooshVideoTranscriptContent)
class VideoTranscriptContent(SchemaConfigured, _DocNumMixin):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshVideoTranscriptContent)

	last_modified = alias('lastModified')

@interface.implementer(search_interfaces.IWhooshAudioTranscriptContent)
class AudioTranscriptContent(SchemaConfigured, _DocNumMixin):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshAudioTranscriptContent)

	last_modified = alias('lastModified')

@interface.implementer(search_interfaces.IWhooshNTICardContent)
class NTICardContent(SchemaConfigured, _DocNumMixin):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(search_interfaces.IWhooshNTICardContent)
	
	content = alias('description')
	last_modified = alias('lastModified')
