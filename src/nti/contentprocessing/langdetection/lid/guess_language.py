# -*- coding: utf-8 -*-
"""
The basic Language identification routines

author = "Damir Cavar <damir@cavar.me>"
http://www.cavar.me/damir/LID/resources/lidtrainer.py.html

Copyright (c) 2008, Kent S Johnson 
https://pypi.python.org/pypi/guess-language
 
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import gzip
import string
import collections
import unicodedata

from .blocks import unicode_block
from ... import space_pattern, non_alpha_pattern
from . import (UNKNOWN, CYRILLIC, ARABIC, DEVANAGARI, SINGLETONS, EXTENDED_LATIN, PT, ALL_LATIN)

MIN_LENGTH = 20

def _load_models(models_dir):
	models = {}
	for model_file in os.listdir(models_dir):
		model_path = os.path.join(models_dir, model_file)
		if os.path.isdir(model_path):
			continue

		if model_file[-3:] == ".gz":
			lang = string.upper(model_file[0]) + model_file[1:-3]
			with gzip.open(model_path) as src:
				model = {}
				for line in src:
					tokens = string.split(line)
					if len(tokens) == 2:
						model[tokens[0]] = float(tokens[1])
			models[lang] = model
	return models

def normalize(u):
	"""
	Convert to normalized unicode.
	Remove non-alpha chars and compress runs of spaces.
	"""
	u = unicodedata.normalize('NFC', u)
	u = non_alpha_pattern.sub(' ', u)
	u = space_pattern.sub(' ', u)
	return u

def find_runs(text):
	"""
	Count the number of characters in each character block
	"""
	run_types = collections.defaultdict(int)

	total_count = 0

	for c in text:
		if c.isalpha():
			block = unicode_block(c)
			run_types[block] += 1
			total_count += 1

	# return run types that used for 40% or more of the string
	# always return basic latin if found more than 15%
	# and extended additional latin if over 10% (for Vietnamese)
	relevant_runs = []
	for key, value in run_types.items():
		pct = (value * 100) / total_count
		if pct >= 40:
			relevant_runs.append(key)
		elif key == "Basic Latin" and pct >= 15:
			relevant_runs.append(key)
		elif key == "Latin Extended Additional" and pct >= 10:
			relevant_runs.append(key)

	return relevant_runs

def _identify(sample, scripts):
	if len(sample) < 3:
		return UNKNOWN

	if 	"Hangul Syllables" in scripts or "Hangul Jamo" in scripts or \
		"Hangul Compatibility Jamo" in scripts or "Hangul" in scripts:
		return "ko"

	if "Greek and Coptic" in scripts:
		return "el"

	if "Katakana" in scripts:
		return "ja"

	if 	"CJK Unified Ideographs" in scripts or "Bopomofo" in scripts or \
		"Bopomofo Extended" in scripts or "KangXi Radicals" in scripts:
		return "zh"

	if "Cyrillic" in scripts:
		return check(sample, CYRILLIC)

	if "Arabic" in scripts or "Arabic Presentation Forms-A" in scripts or "Arabic Presentation Forms-B" in scripts:
		return check(sample, ARABIC)

	if "Devanagari" in scripts:
		return check(sample, DEVANAGARI)

	# Try languages with unique scripts
	for block_name, lang_name in SINGLETONS:
		if block_name in scripts:
			return lang_name

	if "Latin Extended Additional" in scripts:
		return "vi"

	if "Latin-1 Supplement" in scripts or "Latin Extended-A" in scripts or "IPA Extensions" in scripts:
		latinLang = check(sample, EXTENDED_LATIN)
		if latinLang == "pt":
			return check(sample, PT)
		else:
			return latinLang

	if "Basic Latin" in scripts:
		return check(sample, ALL_LATIN)

	return UNKNOWN


def check(sample, models):
	if len(sample) < MIN_LENGTH:
		return UNKNOWN

class _LangDetector(object):

	def __init__(self):
		models_dir = os.path.join(os.path.dirname(__file__), 'models')
		self.models = _load_models(models_dir)

	def __call__(self, text):
		return self._identify(text)

	def _identify(self, content):
		if not content:
			return UNKNOWN

		if isinstance(content, str):
			content = unicode(content, 'utf-8')

		content = normalize(content)

		return _identify(content, find_runs(content))
