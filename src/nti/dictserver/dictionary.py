#!/usr/bin/env python2.7

import sqlite3 as sql
import os
import sys

from zope import interface
import interfaces

class ChromeDictionary(object):

	interface.implements(interfaces.IDictionary)

	def __init__(self, lookupPath):
		if not lookupPath:
			# sqlite accepts an empty path as meaning...what?
			# whatever, it doesn't work
			clz = TypeError if lookupPath is None else LookupError
			raise clz( 'Empty path' )
		self.lookupPath = lookupPath

		try:
			self.connection = sql.connect(self.lookupPath)
			self.cursor = self.connection.cursor()
		except sql.Error:
			_, _, tb = sys.exc_info()

			ex = LookupError( 'No path ' + self.lookupPath )
			raise ex, None, tb


	def lookup(self, word, exact=False):
		if not self.cursor:
			return '{\"error\": \"Invalid sqlite path\"}'

		row = self.__lookup(word)

		if not row and not exact:
			word = word.lower()
			row = self.__lookup(word)

		if not row:
			return '{\"error\": \"%s does not exist in dictionary\"}' % word

		text = row[0]

		text = text.replace('\\"', '"')
		text = text.replace('\\"', '\"')
		text = text.replace('\\\u', '\u')

		return text

	def __lookup(self, word):
		self.cursor.execute('select text from lookup where name = ?', (word,))

		row = self.cursor.fetchone()

		return row

	def close(self):
		if self.connection:
			self.connection.close()
