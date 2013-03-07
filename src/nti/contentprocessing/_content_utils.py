# -*- coding: utf-8 -*-
"""
Content processing utilities

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import six
import difflib

from pkg_resources import resource_filename

from zope import component
from zope import interface

from whoosh.support import levenshtein

from nltk.tokenize import RegexpTokenizer

import repoze.lru

from nti.contentfragments import interfaces as frg_interfaces

from . import default_punk_char_pattern
from . import interfaces as cp_interfaces
from . import default_punk_char_expression
from . import default_word_tokenizer_pattern
from . import default_word_tokenizer_expression

def get_content_translation_table(language='en'):
	table = component.queryUtility(cp_interfaces.IContentTranslationTable, name=language)
	return table or _default_content_translation_table()

@interface.implementer( cp_interfaces.IWordTokenizerExpression )
def _default_word_tokenizer_expression():
	return default_word_tokenizer_expression

@interface.implementer( cp_interfaces.IWordTokenizerPattern )
def _default_word_tokenizer_pattern():
	return default_word_tokenizer_pattern

@interface.implementer( cp_interfaces.IPunctuationCharExpression )
def _default_punctuation_char_expression():
	return default_punk_char_expression

@interface.implementer( cp_interfaces.IPunctuationCharPattern )
def _default_punctuation_char_pattern():
	return default_punk_char_pattern

@repoze.lru.lru_cache(500)
def tokenize_content(text, language='en'):
	tokenizer = component.getUtility(cp_interfaces.IContentTokenizer, name=language)
	result = tokenizer.tokenize(unicode(text)) if text else ()
	return result

split_content = tokenize_content

def get_content(text=None):
	text = unicode(text) if text else None
	result = split_content(text) if text else ()
	result = ' '.join(result)
	return unicode(result)

@interface.implementer( cp_interfaces.IContentTokenizer )
class _ContentTokenizer(object):

	tokenizer = RegexpTokenizer(_default_word_tokenizer_expression(),
								flags = re.MULTILINE | re.DOTALL | re.UNICODE)

	def tokenize(self, content):
		if not content or not isinstance(content, six.string_types):
			return ()

		plain_text = component.getAdapter( content, frg_interfaces.IPlainTextContentFragment, name='text' )
		words = self.tokenizer.tokenize(plain_text)
		return words

@interface.implementer( cp_interfaces.IWordSimilarity )
class _DefaultWordSimilarity(object):

	def compute(self, a, b):
		result = difflib.SequenceMatcher(None, a, b).ratio()
		return result

	def rank(self, word, terms, reverse=True):
		result = sorted(terms, key=lambda w: self.compute(word, w), reverse=reverse)
		return result

class _LevenshteinWordSimilarity(_DefaultWordSimilarity):

	def compute(self, a, b):
		result = levenshtein.relative(a, b)
		return result

def rank_words(word, terms, reverse=True):
	ws = component.getUtility(cp_interfaces.IWordSimilarity)
	result = ws.rank(word, terms, reverse)
	return result

@interface.implementer( cp_interfaces.IContentTranslationTable )
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


