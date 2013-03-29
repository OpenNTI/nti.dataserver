# -*- coding: utf-8 -*-
"""
Whoosh content schemas

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component

from whoosh import fields
from whoosh import analysis

from nti.contentprocessing import default_ngram_maxsize
from nti.contentprocessing import default_ngram_minsize
from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing import default_word_tokenizer_pattern

from . import interfaces as search_interfaces

from .constants import (channel_, content_, keywords_, references_,
					 	recipients_, sharedWith_, replacementContent_, tags_,
						redactionExplanation_, title_, quick_)

# content analyzer

def _ngram_minmax(lang='en'):
	ngc_util = component.queryUtility(cp_interfaces.INgramComputer, name=lang)
	minsize = ngc_util.minsize if ngc_util else default_ngram_minsize
	maxsize = ngc_util.maxsize if ngc_util else default_ngram_maxsize
	return (minsize, maxsize)

def create_ngram_field(lang='en'):
	minsize, maxsize = _ngram_minmax()
	expression = component.queryUtility(cp_interfaces.IWordTokenizerExpression, name=lang) or default_word_tokenizer_pattern
	tokenizer = analysis.RegexTokenizer(expression=expression)
	return fields.NGRAMWORDS(minsize=minsize, maxsize=maxsize, stored=False, tokenizer=tokenizer, at='start')

def create_content_analyzer(lang='en'):
	sw_util = component.queryUtility(search_interfaces.IStopWords, name=lang)
	expression = component.queryUtility(cp_interfaces.IWordTokenizerExpression, name=lang) or default_word_tokenizer_pattern
	stopwords = sw_util.stopwords() if sw_util else ()
	analyzer = 	analysis.StandardAnalyzer(expression=expression, stoplist=stopwords)
	return analyzer

def create_content_field(stored=True):
	return fields.TEXT(stored=stored, spelling=True, phrase=True, analyzer=create_content_analyzer())

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

	def create(self):
		schema = create_default_book_schema()
		return schema

def create_book_schema(name='en'):
	to_call = component.queryUtility(search_interfaces.IWhooshBookSchemaCreator, name=name) or _DefaultBookSchemaCreator()
	return to_call.create()


# UGD types

def _create_user_indexable_content_schema():
	sch = fields.Schema(intid=fields.ID(stored=True, unique=True),
						containerId=fields.ID(stored=False),
						creator=fields.ID(stored=False),
				  		last_modified=fields.DATETIME(stored=False),
				 		ntiid=fields.ID(stored=False))
	return sch

def _create_shareable_schema():
	schema = _create_user_indexable_content_schema()
	schema.add(sharedWith_, fields.TEXT(stored=False))
	return schema

def _create_threadable_schema():
	schema = _create_shareable_schema()
	schema.add(keywords_, fields.KEYWORD(stored=False))
	return schema

def create_highlight_schema():
	schema = _create_threadable_schema()
	schema.add(content_, create_content_field(stored=False))
	schema.add(quick_, create_ngram_field())
	return schema

def create_redaction_schema():
	schema = create_highlight_schema()
	schema.add(replacementContent_, create_content_field(stored=False))
	schema.add(redactionExplanation_, create_content_field(stored=False))
	return schema

def create_note_schema():
	schema = create_highlight_schema()
	schema.add(references_, fields.KEYWORD(stored=False))
	return schema

def create_messageinfo_schema():
	schema = create_note_schema()
	schema.add(channel_, fields.KEYWORD(stored=False))
	schema.add(recipients_, fields.TEXT(stored=False))
	return schema

def create_post_schema():
	schema = _create_shareable_schema()
	schema.add(content_, create_content_field(stored=False))
	schema.add(quick_, create_ngram_field())
	schema.add(title_, fields.TEXT(stored=False))
	schema.add(tags_, fields.KEYWORD(stored=False))
	return schema

class VIDEO_TIMESTAMP(fields.DATETIME):

	@classmethod
	def datetime_to_text(cls, dt):
		result = "%02d:%02d:%02d.%03d" % (dt.hour, dt.minute, dt.second, dt.microsecond)
		return result

	def _parse_datestring(self, qstring):
		# this method parses a very time stamp # hh:mm::ss.uuu
		from whoosh.support.times import adatetime, fix, is_void

		qstring = qstring.replace(" ", "").replace(",", ".")
		year = month = day = 1
		hour = minute = second = microsecond = None
		if len(qstring) >= 2:
			hour = int(qstring[0:2])
		if len(qstring) >= 5:
			minute = int(qstring[3:5])
		if len(qstring) >= 8:
			second = int(qstring[6:8])
		if len(qstring) == 13:
			microsecond = int(qstring[9:13])

		at = fix(adatetime(year, month, day, hour, minute, second, microsecond))
		if is_void(at):
			raise Exception("%r is not a parseable video timestamp" % qstring)
		return at

def create_video_transcript_schema():
	"""
	Video transcript schema

	containerId: NTIID of the video location
	videoId: Video NTIID or custom identifier
	content: transcript text
	quick: transcript text ngrams
	start_timestamp: Start video timestamp
	end_timestamp: End video timestamp
	"""
	sch = fields.Schema(containerId=fields.ID(stored=True, unique=False),
						videoId=fields.ID(stored=True, unique=False),
					 	content=create_content_field(stored=True),
					 	quick=create_ngram_field(),
					 	start_timestamp=VIDEO_TIMESTAMP(stored=True),
					 	end_timestamp=VIDEO_TIMESTAMP(stored=True))
	return sch
