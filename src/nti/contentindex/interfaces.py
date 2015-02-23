#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

####
# Schema
####

class IContentSchemaCreator(interface.Interface):

	def create():
		"""
	 	create a content index schema
		"""

class IBookSchemaCreator(IContentSchemaCreator):
	pass

class IVideoTranscriptSchemaCreator(IContentSchemaCreator):
	pass

class IAudioTranscriptSchemaCreator(IContentSchemaCreator):
	pass

class INTICardSchemaCreator(IContentSchemaCreator):
	pass

####
# Indexer
####

class IContentIndexer(interface.Interface):
	"""
	Creates an index using the contents in a given book
	"""

	def index(content, *args, **kwargs):
		"""
		The content to index

		:param content: The context to index
		"""

class IBookIndexer(IContentIndexer):
	"""
	Creates an index of the content inside a given book
	"""

class IMediaTranscriptIndexer(IContentIndexer):
	"""
	Creates an index for the media transcripts associated with a given content
	"""

class IAudioTranscriptIndexer(IMediaTranscriptIndexer):
	"""
	Creates an index for the audio transcripts associated with a given content
	"""

class IVideoTranscriptIndexer(IMediaTranscriptIndexer):
	"""
	Creates an index for the video transcripts associated with a given content
	"""

class INTICardIndexer(IContentIndexer):
	"""
	Creates an index for the nti cards associated with a given content
	"""
