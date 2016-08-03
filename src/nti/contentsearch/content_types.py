#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.contained import Contained

from nti.common.property import alias

from nti.externalization.representation import WithRepr

from nti.mimetype import mimetype

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from .interfaces import IWhooshBookContent
from .interfaces import IWhooshNTICardContent
from .interfaces import IWhooshAudioTranscriptContent
from .interfaces import IWhooshVideoTranscriptContent

@interface.implementer(IWhooshBookContent)
@WithRepr
@EqHash('docnum',)
class BookContent(SchemaConfigured, Contained):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(IWhooshBookContent)

	intid = alias('docnum')
	last_modified = alias('lastModified')
	containerId = ContainerId = alias('ntiid')

@interface.implementer(IWhooshVideoTranscriptContent)
@WithRepr
@EqHash('docnum',)
class VideoTranscriptContent(SchemaConfigured, Contained):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(IWhooshVideoTranscriptContent)

	last_modified = alias('lastModified')

@interface.implementer(IWhooshAudioTranscriptContent)
@WithRepr
@EqHash('docnum',)
class AudioTranscriptContent(SchemaConfigured, Contained):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(IWhooshAudioTranscriptContent)

	last_modified = alias('lastModified')

@interface.implementer(IWhooshNTICardContent)
@WithRepr
@EqHash('docnum',)
class NTICardContent(SchemaConfigured, Contained):
	__metaclass__ = mimetype.ModeledContentTypeAwareRegistryMetaclass
	createDirectFieldProperties(IWhooshNTICardContent)
	
	content = alias('description')
	last_modified = alias('lastModified')
