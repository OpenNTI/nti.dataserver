#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from nti.schema.field import Object
from nti.schema.field import ValidTextLine

from ..interfaces import IBookIndexer
from ..interfaces import IContentIndexer
from ..interfaces import INTICardIndexer
from ..interfaces import IAudioTranscriptIndexer
from ..interfaces import IVideoTranscriptIndexer

from ..interfaces import IBookSchemaCreator
from ..interfaces import INTICardSchemaCreator
from ..interfaces import IAudioTranscriptSchemaCreator
from ..interfaces import IVideoTranscriptSchemaCreator

class IWhooshBookSchemaCreator(IBookSchemaCreator):
	pass

class IWhooshNTICardSchemaCreator(INTICardSchemaCreator):
	pass

class IWhooshAudioTranscriptSchemaCreator(IAudioTranscriptSchemaCreator):
	pass

class IWhooshVideoTranscriptSchemaCreator(IVideoTranscriptSchemaCreator):
	pass

class IWhooshIndexSpec(interface.Interface):
	content = Object(interface.Interface, required=True, title="Content object")
	indexname = ValidTextLine(title="Index name", required=False)
	indexdir = ValidTextLine(title="Output directory", required=False)

class IWhooshContentIndexer(IContentIndexer):

	def index(content, indexdir=None, indexname=None, optimize=False):
		"""
		Index the specified content 
		
		:param content: Content object
		:param indexdir: Output directory
		:param indexname: Index name
		:param optimize: Optimize index flag
		"""

class IWhooshBookIndexer(IWhooshContentIndexer, IBookIndexer):
	pass

class IWhooshMediaTranscriptIndexer(IWhooshContentIndexer):
	pass

class IWhooshAudioTranscriptIndexer(IWhooshMediaTranscriptIndexer,
									IAudioTranscriptIndexer):
	pass

class IWhooshVideoTranscriptIndexer(IWhooshMediaTranscriptIndexer,
									IVideoTranscriptIndexer):
	pass


class IWhooshNTICardIndexer(IWhooshContentIndexer, INTICardIndexer):
	pass
