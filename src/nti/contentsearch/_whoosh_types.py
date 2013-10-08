# -*- coding: utf-8 -*-
"""
Whoosh content types.

$Id: _whoosh_index.py 24097 2013-09-06 21:09:52Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as search_interfaces

class _MetaSearchWhooshContent(type):

	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		t.mime_type = t.mimeType = 'application/vnd.nextthought.search.%s' % name[1:].lower()
		t.parameters = dict()
		setattr(t, '__external_can_create__', True)
		setattr(t, '__external_class_name__', name[1:])
		return t

@interface.implementer(search_interfaces.IWhooshBookContent)
class _BookContent(SchemaConfigured):
	__metaclass__ = _MetaSearchWhooshContent
	createDirectFieldProperties(search_interfaces.IWhooshBookContent)

	@property
	def intid(self):
		return self.docnum

	@property
	def containerId(self):
		return self.ntiid

@interface.implementer(search_interfaces.IWhooshVideoTranscriptContent)
class _VideoTranscriptContent(SchemaConfigured):
	__metaclass__ = _MetaSearchWhooshContent
	createDirectFieldProperties(search_interfaces.IWhooshVideoTranscriptContent)

	@property
	def ntiid(self):
		return self.videoId

@interface.implementer(search_interfaces.IWhooshNTICardContent)
class _NTICardContent(SchemaConfigured):
	__metaclass__ = _MetaSearchWhooshContent
	createDirectFieldProperties(search_interfaces.IWhooshNTICardContent)
	
	@property
	def content(self):
		return self.description
