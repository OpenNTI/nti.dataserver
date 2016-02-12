#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Various dictionary implementations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import csv
import sqlite3

import simplejson as json

from zope import component
from zope import interface

from nti.dictserver.interfaces import IDictionaryTermData
from nti.dictserver.interfaces import IDictionaryTermDataStorage
from nti.dictserver.interfaces import IJsonDictionaryTermDataStorage
from nti.dictserver.interfaces import IUncleanJsonDictionaryTermDataStorage

@interface.implementer(IJsonDictionaryTermDataStorage)
class SQLiteJsonDictionaryTermDataStorage(object):

	def __init__(self, lookupPath):
		__traceback_info__ = lookupPath
		if not lookupPath:
			# sqlite accepts an empty path as meaning...what?
			# whatever, it doesn't work
			clz = TypeError if lookupPath is None else ValueError
			raise clz('Empty path')
		self.lookupPath = lookupPath

		# FIXME: NOTE: Connection objects are not thread-safe.
		# We happen to be working OK because we operate using greenlets
		# and there's no chance to switch greenlets (sqlite3 being implemented in C)
		self.connection = sqlite3.connect(self.lookupPath)

	def lookup(self, word, exact=False):
		text = self.__lookup(word)

		if not text and not exact:
			word = word.lower()
			text = self.__lookup(word)

		if not text:
			return '{\"error\": \"%s does not exist in dictionary\"}' % word

		text = text.replace('\\"', '"')
		text = text.replace('\\"', '\"')
		text = text.replace(b'\\\u', b'\u')
		return text

	def __lookup(self, word):
		cursor = self.connection.execute('select text from lookup where name = ?', (word,))

		row = cursor.fetchone()
		text = row[0] if row else None
		cursor.close()

		return text

	def close(self):
		self.connection.close()
		# From now on we will throw sqlite3.ProgrammingError

@interface.implementer(IUncleanJsonDictionaryTermDataStorage)
class UncleanSQLiteJsonDictionaryTermStorage(SQLiteJsonDictionaryTermDataStorage):
	pass

def _wiki_clean(defn, lang='en'):
	if not defn:
		return defn
	defn = re.sub("\{\{.*?\}\}", "", defn).replace('[[', '').replace(']]', '').strip()
	return defn.replace('http://%s.wiktionary.org/wiki/' % lang, '')

@interface.implementer(IDictionaryTermDataStorage)
@component.adapter(IJsonDictionaryTermDataStorage)
class JsonDictionaryTermDataStorage(object):
	"""
	Adapts JSON storage to real term objects.
	"""

	_need_to_clean = False

	def __init__(self, context):
		self.context = context
		if IUncleanJsonDictionaryTermDataStorage.providedBy(context):
			self._need_to_clean = True

	def lookup(self, word, exact=False, lang='en'):
		json_string = self.context.lookup(word, exact=exact)
		if not json_string:
			return
		__traceback_info__ = json_string
		try:
			term = json.loads(json_string)
		except (ValueError, TypeError):
			# Bad JSON Data
			logger.exception("Bad json data for %s", word)
			term = None

		if term and 'error' not in term:
			result = DictionaryTermData(term)
			if self._need_to_clean:
				result['etymology'] = _wiki_clean(result.get('etymology'), lang)
				for meaning_dict in result.get('meanings', ()):
					meaning_dict['content'] = _wiki_clean(meaning_dict['content'])
			return result

@interface.implementer(IDictionaryTermDataStorage)
class TrivialExcelCSVDataStorage(object):
	"""
	Reads a CSV file containing a ``Term`` and ``Definition`` column
	and stores this data in memory.
	"""

	def __init__(self, path_or_file):
		"""
		:param path_or_file: Either a string naming a file path, or an open
			file-like object that we can read from.
		"""

		if isinstance(path_or_file, basestring):
			path_or_file = open(path_or_file, 'rU')

		# CSV Readers operate at the level of bytestrings, so it's up to us
		# to decode
		reader = csv.DictReader(path_or_file)
		self._data = {}  # depending on how big the data is, we might want to use a btree
		for row in reader:
			term = row['Term'].decode('utf-8')
			defn = row['Definition'].decode('utf-8')
			self._data[term.lower()] = DictionaryTermData(meanings=({'content': defn,
																	 'examples': (),
																	 'type': 'noun' },))

	def lookup(self, key, exact=False):
		result = self._data.get(key)
		if not result and not exact:
			result = self._data.get(key.lower())
		return result

@interface.implementer(IDictionaryTermData)
class DictionaryTermData(dict):
	pass
