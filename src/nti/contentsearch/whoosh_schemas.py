#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh content schemas

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from whoosh import fields
from whoosh import analysis

from nti.contentprocessing import default_ngram_maxsize
from nti.contentprocessing import default_ngram_minsize
from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing import default_word_tokenizer_pattern

from . import common
from . import interfaces as search_interfaces

# content analyzer

def _ngram_min_max(lang='en'):
	ngc_util = component.queryUtility(cp_interfaces.INgramComputer, name=lang)
	minsize = ngc_util.minsize if ngc_util else default_ngram_minsize
	maxsize = ngc_util.maxsize if ngc_util else default_ngram_maxsize
	return (minsize, maxsize)

def create_ngram_field(lang='en', at='start'):
	minsize, maxsize = _ngram_min_max()
	expression = \
		component.queryUtility(cp_interfaces.IWordTokenizerExpression, name=lang) or \
		default_word_tokenizer_pattern
	tokenizer = analysis.RegexTokenizer(expression=expression)
	analyzer = analysis.NgramWordAnalyzer(minsize=minsize, maxsize=maxsize,
										  tokenizer=tokenizer, at=at)
	return fields.TEXT(analyzer=analyzer, phrase=False)

def create_content_analyzer(lang='en'):
	sw_util = component.queryUtility(search_interfaces.IStopWords)
	stopwords = sw_util.stopwords(lang) if sw_util is not None else ()
	expression = \
		component.queryUtility(cp_interfaces.IWordTokenizerExpression, name=lang) or \
		default_word_tokenizer_pattern
	analyzer = 	analysis.StandardAnalyzer(expression=expression, stoplist=stopwords)
	return analyzer

def create_content_field(stored=True):
	return fields.TEXT(stored=stored, spelling=True, phrase=True,
					   analyzer=create_content_analyzer())

# book content

def create_default_book_schema():
	"""
	Book index schema

	docid: Unique id
	ntiid: Internal nextthought ID for the chapter/section
	title: chapter/section title
	last_modified: chapter/section last modification since the epoch
	keywords: chapter/section key words
	content: chapter/section text
	quick: chapter/section text ngrams
	related: ntiids of related sections
	ref: chapter reference
	"""
	sch = fields.Schema(docid=fields.ID(stored=True, unique=False),
						ntiid=fields.ID(stored=True, unique=False),
						title=fields.TEXT(stored=True, spelling=True),
					  	last_modified=fields.DATETIME(stored=True),
					  	keywords=fields.KEYWORD(stored=True),
					    quick=create_ngram_field(),
					 	related=fields.KEYWORD(stored=True),
					 	content=create_content_field(stored=True))
	return sch

@interface.implementer(search_interfaces.IWhooshBookSchemaCreator)
class _DefaultBookSchemaCreator(object):

	singleton = None
	__slots__ = ()

	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(_DefaultBookSchemaCreator, cls).__new__(cls)
		return cls.singleton

	def create(self):
		schema = create_default_book_schema()
		return schema

def create_book_schema(name='en'):
	to_call = component.queryUtility(search_interfaces.IWhooshBookSchemaCreator,
									 name=name) or _DefaultBookSchemaCreator()
	return to_call.create()

class VIDEO_TIMESTAMP(fields.DATETIME):

	def _parse_datestring(self, qstring):
		result = common.videotimestamp_to_datetime(qstring)
		return result

	def __setstate__(self, d):
		d['bits'] = 64
		d['numtype'] = int
		super(VIDEO_TIMESTAMP, self).__setstate__(d)

def create_video_transcript_schema():
	"""
	Video transcript schema

	containerId: NTIID of the video location
	videoId: Video NTIID or custom identifier
	title: Video title
	content: transcript text
	quick: transcript text ngrams
	keywords: transcript keywords
	start_timestamp: Start video timestamp
	end_timestamp: End video timestamp
	"""
	sch = fields.Schema(containerId=fields.ID(stored=True, unique=False),
						videoId=fields.ID(stored=True, unique=False),
						language=fields.ID(stored=True, unique=False),
						title=create_content_field(stored=True),
					 	content=create_content_field(stored=True),
					 	quick=create_ngram_field(),
					 	keywords=fields.KEYWORD(stored=True),
					 	start_timestamp=VIDEO_TIMESTAMP(stored=True),
					 	end_timestamp=VIDEO_TIMESTAMP(stored=True),
					 	last_modified=fields.DATETIME(stored=True))
	return sch

@interface.implementer(search_interfaces.IWhooshVideoTranscriptSchemaCreator)
class _DefaultVideoTranscriptSchemaCreator(object):

	singleton = None
	__slots__ = ()

	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(_DefaultVideoTranscriptSchemaCreator, cls).__new__(cls)
		return cls.singleton

	def create(self):
		schema = create_video_transcript_schema()
		return schema

def create_audio_transcript_schema():
	"""
	Audio transcript schema

	containerId: NTIID of the audio location
	audioId: Audio NTIID or custom identifier
	title: Audio title
	content: transcript text
	quick: transcript text ngrams
	keywords: transcript keywords
	start_timestamp: Start video timestamp
	end_timestamp: End video timestamp
	"""
	sch = fields.Schema(containerId=fields.ID(stored=True, unique=False),
						audioId=fields.ID(stored=True, unique=False),
						language=fields.ID(stored=True, unique=False),
						title=create_content_field(stored=True),
					 	content=create_content_field(stored=True),
					 	quick=create_ngram_field(),
					 	keywords=fields.KEYWORD(stored=True),
					 	start_timestamp=VIDEO_TIMESTAMP(stored=True),
					 	end_timestamp=VIDEO_TIMESTAMP(stored=True),
					 	last_modified=fields.DATETIME(stored=True))
	return sch

@interface.implementer(search_interfaces.IWhooshAudioTranscriptSchemaCreator)
class _DefaultAudioTranscriptSchemaCreator(object):

	singleton = None
	__slots__ = ()

	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(_DefaultAudioTranscriptSchemaCreator, cls).__new__(cls)
		return cls.singleton

	def create(self):
		schema = create_audio_transcript_schema()
		return schema

def create_nti_card_schema():
	"""
	Card schema

	ntiid: card NTIID
	type: card type
	title: card title
	content: card description
	quick: card text ngrams
	creator: card creator
	target_ntiid: card target hyperlink.
	"""
	sch = fields.Schema(containerId=fields.ID(stored=True, unique=False),
						ntiid=fields.ID(stored=True, unique=True),
						type=fields.ID(stored=True),
						title=create_content_field(stored=True),
					 	content=create_content_field(stored=True),
					 	quick=create_ngram_field(),
					 	creator=fields.ID(stored=True),
					 	href=fields.ID(stored=True),
					 	target_ntiid=fields.ID(stored=True),
					 	last_modified=fields.DATETIME(stored=True))
	return sch

@interface.implementer(search_interfaces.IWhooshNTICardSchemaCreator)
class _DefaultNTICardSchemaCreator(object):

	singleton = None
	__slots__ = ()

	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(_DefaultNTICardSchemaCreator, cls).__new__(cls)
		return cls.singleton

	def create(self):
		schema = create_nti_card_schema()
		return schema
