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

from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.schema import SchemaConfigured

from .trigram_trainer import calc_prob
from .trigram_trainer import TrainerData
from .blocks import BLOCKS, BLOCK_RSHIFT
from .. import interfaces as ld_interfaces
from .trigram_trainer import create_trigram_nsc
from ... import space_pattern, non_alpha_pattern
from . import (UNKNOWN, CYRILLIC, ARABIC, DEVANAGARI, SINGLETONS, EXTENDED_LATIN, PT,
			   ALL_LATIN, NAME_MAP, WORD_RE)

def _load_models(models_dir):
	models = {}
	for model_file in os.listdir(models_dir):
		model_path = os.path.join(models_dir, model_file)
		if os.path.isdir(model_path):
			continue

		if model_file[-3:] == ".gz":
			lang = string.lower(model_file[0:-3])
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

	words = WORD_RE.findall(text.replace("’", "'"))
	for word in words:
		for char in word:
			block = BLOCKS[ord(char) >> BLOCK_RSHIFT]
			run_types[block] += 1
			total_count += 1

	# return run types that used for 40% or more of the string
	# always return basic latin if found more than 15%
	relevant_runs = []
	for key, value in run_types.items():
		pct = (value * 100) / total_count
		if pct >= 40:
			relevant_runs.append(key)
		elif key == "Basic Latin" and pct >= 15:
			relevant_runs.append(key)

	return relevant_runs

def _identify(sample, scripts, models):

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
		return _check(sample, models, CYRILLIC)

	if "Arabic" in scripts or "Arabic Presentation Forms-A" in scripts or "Arabic Presentation Forms-B" in scripts:
		return _check(sample, models, ARABIC)

	if "Devanagari" in scripts:
		return _check(sample, models, DEVANAGARI)

	# Try languages with unique scripts
	for block_name, lang_name in SINGLETONS:
		if block_name in scripts:
			return lang_name

	if	"Extended Latin" in scripts:
		latin_lang = _check(sample, models, EXTENDED_LATIN)
		if latin_lang == "pt":
			return _check(sample, models, PT)
		else:
			return latin_lang

	if "Basic Latin" in scripts:
		return _check(sample, models, ALL_LATIN)

	return UNKNOWN

def _check(text, models, langs):
	td = TrainerData()

	create_trigram_nsc(text, td)  # create trigrams of submitted text
	calc_prob(td)  # calculate probabilities

	result = collections.defaultdict(float)  # storage for the matches with the models
	for lang in langs:
		result[lang] = 0

	# for all keys in trigrams
	for x in td.trigrams.keys():
		# for 0 to number language models
		for lang in langs:
			model = models.get(lang, None)
			if model and x in model:
				# if the model contains the key, get the deviation
				value = model[x] - td.trigrams[x]
				if value < 0:
					value = value * -1
				result[lang] += value
			else:
				# otherwise set the resulting value to 1 = max. deviation
				result[lang] += 1

	result_lang = UNKNOWN
	value = float(1.0)

	for lang in langs:
		result[lang] = float(result[lang]) / float(td.total_trigrams)
		if value > result[lang]:
			value = float(result[lang])
			result_lang = lang

	return result_lang


@interface.implementer(ld_interfaces.ILanguage)
class _Language(SchemaConfigured):

	code = FP(ld_interfaces.ILanguage['code'])
	name = FP(ld_interfaces.ILanguage['name'])

	def __str__(self):
		return self.code

	def __repr__(self):
		return "(%s,%s)" % (self.code, self.name)

	def __eq__(self, other):
		try:
			return self is other or self.code == other.code
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.code)
		return xhash

@interface.implementer(ld_interfaces.ILanguageDetector)
class _LangDetector(object):

	def __init__(self):
		models_dir = os.path.join(os.path.dirname(__file__), 'models')
		self.models = _load_models(models_dir)

	def __call__(self, text):
		lang = self._identify(text)
		if lang and lang != UNKNOWN:
			result = _Language(code=lang, name=NAME_MAP.get(lang))
			return result
		return None

	def _identify(self, content):
		if not content:
			return UNKNOWN

		if isinstance(content, str):
			content = unicode(content, 'utf-8')

		content = normalize(content)

		return _identify(content, find_runs(content), self.models)
