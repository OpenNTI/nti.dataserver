#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Various dictionary implementations.
$Id$
"""
from __future__ import print_function, unicode_literals

import sqlite3


from zope import interface
from zope.deprecation import deprecated

from nti.dictserver import interfaces

@interface.implementer(interfaces.IJsonDictionary)
class SQLiteJsonDictionary(object):

	def __init__(self, lookupPath):
		__traceback_info__ = lookupPath
		if not lookupPath:
			# sqlite accepts an empty path as meaning...what?
			# whatever, it doesn't work
			clz = TypeError if lookupPath is None else ValueError
			raise clz( 'Empty path' )
		self.lookupPath = lookupPath

		# FIXME: NOTE: Connection objects are not thread-safe.
		# We happen to be working OK because we operate using greenlets
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

ChromeDictionary = SQLiteJsonDictionary
deprecated( 'ChromeDictionary', 'Prefer SQLiteJsonDictionary' )
