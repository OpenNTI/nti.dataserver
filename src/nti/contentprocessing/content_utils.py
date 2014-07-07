#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content processing utilities

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import difflib
import unicodedata
from six import string_types

from pkg_resources import resource_filename

from zope import component
from zope import interface

try:
	from zopyx.txng3.ext.levenshtein import ratio as relative
except ImportError:
	from whoosh.support.levenshtein import relative

from nltk.tokenize import RegexpTokenizer

import repoze.lru

from nti.contentfragments.interfaces import IPlainTextContentFragment

from . import space_pattern
from . import non_alpha_pattern
from . import special_regexp_chars
from . import default_punk_char_pattern
from . import interfaces as cp_interfaces
from .interfaces import IContentTokenizer
from . import default_punk_char_expression
from . import default_word_tokenizer_pattern
from . import default_punk_char_pattern_plus
from . import default_word_tokenizer_expression
from . import default_punk_char_expression_plus

def get_content_translation_table(lang='en'):
	table = component.queryUtility(cp_interfaces.IContentTranslationTable, name=lang)
	return table or _default_content_translation_table()

@interface.implementer(cp_interfaces.IWordTokenizerExpression)
def _default_word_tokenizer_expression():
	return default_word_tokenizer_expression

@interface.implementer(cp_interfaces.IWordTokenizerPattern)
def _default_word_tokenizer_pattern():
	return default_word_tokenizer_pattern

@interface.implementer(cp_interfaces.IPunctuationCharExpression)
def _default_punctuation_char_expression():
	return default_punk_char_expression

@interface.implementer(cp_interfaces.IPunctuationCharPattern)
def _default_punctuation_char_pattern():
	return default_punk_char_pattern

@interface.implementer(cp_interfaces.IPunctuationCharExpressionPlus)
def _default_punctuation_char_expression_plus():
	return default_punk_char_expression_plus

@interface.implementer(cp_interfaces.IPunctuationCharPatternPlus)
def _default_punctuation_char_pattern_plus():
	return default_punk_char_pattern_plus

@repoze.lru.lru_cache(500)
def tokenize_content(text, lang='en'):
	if not text or not isinstance(text, string_types):
		return ()

	tokenizer = component.getUtility(IContentTokenizer, name=lang)
	result = tokenizer.tokenize(text)
	return result

split_content = tokenize_content

def get_content(text=None, lang="en"):
	if not text or not isinstance(text, string_types):
		return ''

	result = tokenize_content(text, lang)
	result = ' '.join(result)
	return result

def normalize(u, form='NFC'):
	"""
	Convert to normalized unicode.
	Remove non-alpha chars and compress runs of spaces.
	"""
	u = unicodedata.normalize(form, u)
	u = non_alpha_pattern.sub(' ', u)
	u = space_pattern.sub(' ', u)
	return u

@interface.implementer(cp_interfaces.IContentTokenizer)
class _ContentTokenizer(object):

	__slots__ = ()

	tokenizer = RegexpTokenizer(_default_word_tokenizer_expression(),
								flags=re.MULTILINE | re.DOTALL | re.UNICODE)

	@classmethod
	def tokenize(cls, content):
		if not content or not isinstance(content, string_types):
			return ()

		plain_text = cls.to_plain_text(content)
		return cls.tokenizer.tokenize(plain_text)


	@classmethod
	def to_plain_text(cls, content):
		text = component.getAdapter(content,
									IPlainTextContentFragment,
									name='text')
		return text


@interface.implementer(cp_interfaces.IWordSimilarity)
class _BaseWordSimilarity(object):

	def compute(self, a, b):
		return 0

	def rank(self, word, terms, reverse=True):
		result = sorted(terms, key=lambda w: self.compute(word, w), reverse=reverse)
		return result

class _SequenceMatcherWordSimilarity(_BaseWordSimilarity):

	def compute(self, a, b):
		result = difflib.SequenceMatcher(None, a, b).ratio()
		return result

class _LevenshteinWordSimilarity(_BaseWordSimilarity):

	def compute(self, a, b):
		result = relative(a, b)
		return result

def rank_words(word, terms, reverse=True):
	ws = component.getUtility(cp_interfaces.IWordSimilarity)
	result = ws.rank(word, terms, reverse)
	return result

default_trans_table = None

@interface.implementer(cp_interfaces.IContentTranslationTable)
def _default_content_translation_table():

	global default_trans_table

	if default_trans_table is None:
		name = resource_filename(__name__, "punctuation-en.txt")
		with open(name, 'r') as src:
			lines = src.readlines()

		default_trans_table = {}
		for line in lines:
			line = line.replace('\n', '')
			splits = line.split('\t')
			repl = splits[4] or None if len(splits) >= 5 else None
			default_trans_table[int(splits[0])] = repl

	return default_trans_table

def clean_special_characters(source, replacement=u''):
	"""
	remove regular expression special chars
	"""
	if source:
		for c in special_regexp_chars:
			source = source.replace(c, replacement)
	return source
