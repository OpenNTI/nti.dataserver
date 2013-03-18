# -*- coding: utf-8 -*-
"""
Spambayes tokenizer

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
import math

from zope import component
from zope import interface

from nti.contentprocessing import interfaces as cp_interfaces

from . import LN2
from ._stripper import has_highbit_char
from . import interfaces as sps_interfaces
from ._stripper import _default_translation_table
from ._stripper import (crack_uuencode, crack_urls, crack_html_style, crack_html_comment, crack_noframes)
from ._stripper import (word_re, numeric_entity_re, breaking_entity_re, html_re, find_html_virus_clues,
						numeric_entity_replacer)

def log2(n, log=math.log, c=LN2):
	return log(n) / c

def get_content_translation_table():
	table = component.queryUtility(cp_interfaces.IContentTranslationTable, name="spambayes")
	return table or _default_translation_table()

def tokenize_word(word, *args, **kwargs):
	settings = component.getUtility(sps_interfaces.ITokenizerSettings)
	min_word_size = kwargs.get('min_word_size', settings.min_word_size)
	max_word_size = kwargs.get('max_word_size', settings.max_word_size)
	generate_long_skips = kwargs.get('generate_long_skips', settings.generate_long_skips)

	n = len(word)

	# make sure this range matches in tokenize().
	if min_word_size <= n <= max_word_size:
		yield word
	elif n >= min_word_size:
		# a long word.

		# don't want to skip embedded email addresses.
		# An earlier scheme also split up the y in x@y on '.'.  Not splitting
		# improved the f-n rate; the f-p rate didn't care either way.
		if n < 40 and '.' in word and word.count('@') == 1:
			p1, p2 = word.split('@')
			yield 'email name:' + p1
			yield 'email addr:' + p2
		else:
			# there's value in generating a token indicating roughly how
			# many chars were skipped.  This has real benefit for the f-n
			# rate, but is neutral for the f-p rate.  I don't know why!
			# XXX Figure out why, and/or see if some other way of summarizing
			# XXX this info has greater benefit.
			if generate_long_skips:
				yield "skip:%c %d" % (word[0], n // 10 * 10)

			if has_highbit_char(word):
				hicount = 0
				for i in map(ord, word):
					if i >= 128:
						hicount += 1
					yield "8bit%%:%d" % round(hicount * 100.0 / len(word))


def check_word(word):
	result = word_re.findall(word) if word else ()
	return word if len(result) != 1 else result[0]

def tokenize_text(text, *args, **kwargs):
	"""
	Tokenize everything in the chunk of text we were handed.
	"""
	settings = component.getUtility(sps_interfaces.ITokenizerSettings)
	do_short_runs = kwargs.get('short_runs', settings.short_runs)
	min_word_size = kwargs.get('min_word_size', settings.min_word_size)
	max_word_size = kwargs.get('max_word_size', settings.max_word_size)

	short_count = 0
	short_runs = set()
	for w in text.split():
		# remove any punkt signs
		w = check_word(w)

		n = len(w)
		if n < min_word_size:
			# count how many short words we see in a row - meant to
			# latch onto crap like this:
			# X j A m N j A d X h
			# M k E z R d I p D u I m A c
			# C o I d A t L j I v S j
			short_count += 1
		else:
			if short_count:
				short_runs.add(short_count)
				short_count = 0
			# make sure this range matches in tokenize_word().
			if min_word_size <= n <= max_word_size:
				yield w

			elif n >= min_word_size:
				for t in tokenize_word(w, *args, **kwargs):
					yield t
	if short_runs and do_short_runs:
		yield "short:%d" % int(log2(max(short_runs)))


def tokenize(text, *args, **kwargs):

	settings = component.getUtility(sps_interfaces.ITokenizerSettings)
	replace_nonascii_chars = kwargs.get('replace_nonascii_chars', settings.replace_nonascii_chars)

	# replace numeric character entities (like &#97; for the letter # 'a').
	text = numeric_entity_re.sub(numeric_entity_replacer, text)

	# normalize case.
	text = text.lower()

	if replace_nonascii_chars:
		text = text.translate(get_content_translation_table())

	for t in find_html_virus_clues(text):
		yield "virus:%s" % t

	# get rid of uuencoded sections, embedded URLs, <style gimmicks,
	# and html comments.
	for cracker in (crack_uuencode,
					crack_urls,
					crack_html_style,
					crack_html_comment,
					crack_noframes):
		text, tokens = cracker(text)
		for t in tokens:
			yield t

	# remove html/xml tags.  also &nbsp;.  <br> and <p> tags should
	# create a space too.
	text = breaking_entity_re.sub(' ', text)

	# it's important to eliminate html tags rather than, e.g.,
	# replace them with a blank (as this code used to do), else
	# simple tricks like
	#    Wr<!$FS|i|R3$s80sA >inkle Reduc<!$FS|i|R3$s80sA >tion
	# can be used to disguise words.  <br> and <p> were special-
	# cased just above (because browsers break text on those,
	# they can't be used to hide words effectively).
	text = html_re.sub('', text)

	for t in tokenize_text(text, *args, **kwargs):
		yield t

@interface.implementer(cp_interfaces.IContentTokenizer)
class _ContentTokenizer(object):

	def tokenize(self, text, *args, **kwargs):
		if not text or not isinstance(text, six.string_types):
			result = ()
		else:
			result = list(tokenize(text, *args, **kwargs))
		return result
