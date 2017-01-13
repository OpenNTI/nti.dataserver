#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.location.interfaces import IContained

from zope.mimetype.interfaces import IContentTypeAware

from nti.contentsearch.interfaces import ISearchHit
from nti.contentsearch.interfaces import ITranscriptSearchHit
from nti.contentsearch.interfaces import IContentUnitSearchHit
from nti.contentsearch.interfaces import IUserGeneratedDataSearchHit

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

@WithRepr
@interface.implementer(IContained, IContentTypeAware)
class SearchHitMixin(object):

	__parent__ = None
	__name__ = alias('ID')
	__external_class_name__  = 'Hit'
	
	id = alias('ID')
	ContainerId = alias('Containers')
	createdTime = alias('lastModified')
	
	parameters = {}
	
	def __init__(self, *args, **kwargs):
		super(SearchHitMixin, self).__init__(*args, **kwargs)

	@property
	def Query(self):
		return getattr(self.__parent__, 'Query', None)

	def __eq__(self, other):
		try:
			return self is other or self.ID == other.ID
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.ID)
		return xhash

@interface.implementer(ISearchHit)
class SearchHit(SchemaConfigured, SearchHitMixin):
	createDirectFieldProperties(ISearchHit)
	
	mime_type = mimeType = 'application/vnd.nextthought.search.searchhit'

@interface.implementer(ITranscriptSearchHit)
class TranscriptSearchHit(SchemaConfigured, SearchHitMixin):
	createDirectFieldProperties(ITranscriptSearchHit)

	mime_type = mimeType = 'application/vnd.nextthought.search.transcriptsearchhit'

@interface.implementer(IContentUnitSearchHit)
class ContentUnitSearchHit(SchemaConfigured, SearchHitMixin):
	createDirectFieldProperties(IContentUnitSearchHit)

	mime_type = mimeType = 'application/vnd.nextthought.search.contentunitsearchhit'

@interface.implementer(IUserGeneratedDataSearchHit)
class UserGeneratedDataSearchHit(SchemaConfigured, SearchHitMixin):
	createDirectFieldProperties(IUserGeneratedDataSearchHit)

	mime_type = mimeType = 'application/vnd.nextthought.search.ugdsearchhit'
