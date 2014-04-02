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
import six
import difflib
import unicodedata

from pkg_resources import resource_filename

from zope import component
from zope import interface

try:
	from zopyx.txng3.ext.levenshtein import ratio as relative
except ImportError:
	from whoosh.support.levenshtein import relative

from nltk.tokenize import RegexpTokenizer

import repoze.lru

from nti.contentfragments import interfaces as frg_interfaces

from . import space_pattern
from . import non_alpha_pattern
from . import special_regexp_chars
from . import default_punk_char_pattern
from . import interfaces as cp_interfaces
from . import default_punk_char_expression
from . import default_word_tokenizer_pattern
from  .import default_punk_char_pattern_plus
from . import default_word_tokenizer_expression
from  .import default_punk_char_expression_plus

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
	tokenizer = component.getUtility(cp_interfaces.IContentTokenizer, name=lang)
	result = tokenizer.tokenize(unicode(text)) if text else ()
	return result

split_content = tokenize_content

def get_content(text=None, lang="en"):
	text = unicode(text) if text else None
	result = split_content(text, lang) if text else ()
	result = ' '.join(result)
	return unicode(result)

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

	tokenizer = RegexpTokenizer(_default_word_tokenizer_expression(),
								flags=re.MULTILINE | re.DOTALL | re.UNICODE)

	def tokenize(self, content):
		if content and isinstance(content, six.string_types):
			plain_text = self.to_plain_text(content)
			words = self.tokenizer.tokenize(plain_text)
		else:
			words = ()
		return words

	@classmethod
	def to_plain_text(cls, content):
		text = \
			component.getAdapter(content,
								 frg_interfaces.IPlainTextContentFragment, name='text')
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

@interface.implementer(cp_interfaces.IContentTranslationTable)
def _default_content_translation_table():

	name = resource_filename(__name__, "punctuation-en.txt")
	with open(name, 'r') as src:
		lines = src.readlines()

	result = {}
	for line in lines:
		line = line.replace('\n', '')
		splits = line.split('\t')
		repl = splits[4] or None if len(splits) >= 5 else None
		result[int(splits[0])] = repl
	return result

def clean_special_characters(source, replacement=u''):
	"""
	remove regular expression special chars
	"""
	if source:
		for c in special_regexp_chars:
			source = source.replace(c, replacement)
	return source
