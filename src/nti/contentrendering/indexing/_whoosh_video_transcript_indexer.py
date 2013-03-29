# -*- coding: utf-8 -*-
"""
Whoosh video transcript indexers.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.contentsearch import interfaces as search_interfaces

from . import interfaces as cridxr_interfaces
from ._common_indexer import _BasicWhooshIndexer

@interface.implementer(cridxr_interfaces.IWhooshVideoTranscriptIndexer)
class _WhooshVideoTranscriptIndexer(_BasicWhooshIndexer):

	def get_schema(self, name='en'):
		creator = component.getUtility(search_interfaces.IWhooshBookSchemaCreator, name=name)
		return creator.create()

	def process_book(self, book, writer, language='en'):
		pass

_DefaultWhooshVideoTranscriptIndexer = _WhooshVideoTranscriptIndexer
