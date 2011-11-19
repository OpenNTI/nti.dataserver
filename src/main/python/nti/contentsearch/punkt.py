# Natural Language Toolkit: Punkt sentence tokenizer
#
# Copyright (C) 2001-2011 NLTK Project
# Algorithm: Kiss & Strunk (2006)
# Author: Willy <willy@csse.unimelb.edu.au> (original Python port)
#         Steven Bird <sb@csse.unimelb.edu.au> (additions)
#         Edward Loper <edloper@gradient.cis.upenn.edu> (rewrite)
#         Joel Nothman <jnothman@student.usyd.edu.au> (almost rewrite)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id: probability.py 4865 2007-07-11 22:6:07Z edloper $

"""
The Punkt sentence tokenizer.  The algorithm for this tokenizer is
described in Kiss & Strunk (2006)::

Kiss, Tibor and Strunk, Jan (2006): Unsupervised Multilingual Sentence
Boundary Detection.  Computational Linguistics 32: 485-525.
"""

import re

######################################################################
#{ Language-dependent variables
######################################################################

class PunktLanguageVars(object):
	"""
	Stores variables, mostly regular expressions, which may be
	language-dependent for correct application of the algorithm.
	An extension of this class may modify its properties to suit
	a language other than English; an instance can then be passed
	as an argument to PunktSentenceTokenizer and PunktTrainer
	constructors.
	"""
	
	__slots__ = ('_re_period_context', '_re_word_tokenizer')
	
	sent_end_chars = ('.', '?', '!')
	"""Characters which are candidates for sentence boundaries"""
	
	@property
	def _re_sent_end_chars(self):
		return '[%s]' % re.escape(''.join(self.sent_end_chars))
	
	internal_punctuation = ',:;' # might want to extend this..
	"""sentence internal punctuation, which indicates an abbreviation if
	preceded by a period-final token."""
	
	re_boundary_realignment = re.compile(r'["\')\]}]+?(?:\s+|(?=--)|$)', re.MULTILINE)
	"""Used to realign punctuation that should be included in a sentence
	although it follows the period (or ?, !)."""
	
	_re_word_start    = r"[^\(\"\`{\[:;&\#\*@\)}\]\-,]"
	"""Excludes some characters from starting word tokens"""
	
	_re_non_word_chars   = r"(?:[?!)\";}\]\*:@\'\({\[])"
	"""Characters that cannot appear within words"""
	
	_re_multi_char_punct = r"(?:\-{2,}|\.{2,}|(?:\.\s){2,}\.)"
	"""Hyphen and ellipsis are multi-character punctuation"""
	
	_word_tokenize_fmt = r'''(
		%(MultiChar)s
		|
		(?=%(WordStart)s)\S+?  # Accept word characters until end is found
		(?= # Sequences marking a word's end
		\s|                                 # White-space
		$|                                  # End-of-string
		%(NonWord)s|%(MultiChar)s|          # Punctuation
		,(?=$|\s|%(NonWord)s|%(MultiChar)s) # Comma if at end of word
		)
		|
		\S
		)'''
	"""Format of a regular expression to split punctuation from words,
	excluding period."""
	
	def _word_tokenizer_re(self):
		"""Compiles and returns a regular expression for word tokenization"""
		try:
			return self._re_word_tokenizer
		except AttributeError:
			self._re_word_tokenizer = re.compile(
				self._word_tokenize_fmt %
				{
					'NonWord':   self._re_non_word_chars,
					'MultiChar': self._re_multi_char_punct,
					'WordStart': self._re_word_start,
				},
				re.UNICODE | re.VERBOSE
			)
			return self._re_word_tokenizer
		
	def word_tokenize(self, s, remove_punkt=False, wordpat=r"(?L)\w+"):
		"""Tokenize a string to split of punctuation other than periods"""
		result = self._word_tokenizer_re().findall(s)
		if remove_punkt and wordpat:
			result = re.findall(wordpat, s)
		return result
		
	_period_context_fmt = r"""
		\S*                          # some word material
		%(SentEndChars)s             # a potential sentence ending
		(?=(?P<after_tok>
		    %(NonWord)s              # either other punctuation
		    |
		    \s+(?P<next_tok>\S+)     # or whitespace and some other token
		))"""
	"""Format of a regular expression to find contexts including possible
	sentence boundaries. Matches token which the possible sentence boundary
	ends, and matches the following token within a lookahead expression."""
	
	def period_context_re(self):
		"""Compiles and returns a regular expression to find contexts
		including possible sentence boundaries."""
		try:
			return self._re_period_context
		except:
			self._re_period_context = re.compile(
				self._period_context_fmt %
				{
					'NonWord':      self._re_non_word_chars,
					'SentEndChars': self._re_sent_end_chars,
				},
				re.UNICODE | re.VERBOSE)
		return self._re_period_context

_re_non_punct = re.compile(r'[^\W\d]', re.UNICODE)
"""Matches token types that are not merely punctuation. (Types for
numeric tokens are changed to ##number## and hence contain alpha.)"""


######################################################################
#{ Punkt Word Tokenizer
######################################################################

class PunktWordTokenizer(object):
	def __init__(self, lang_vars=PunktLanguageVars()):
		self._lang_vars = lang_vars
	
	def tokenize(self, text, remove_punkt=False, wordpat=r"(?L)\w+"):
		return self._lang_vars.word_tokenize(text, remove_punkt, wordpat)
