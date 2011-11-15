#!/usr/bin/env python2.7

import sqlite3 as sql
import os

from zope import interface
import interfaces

class ChromeDictionary(object):

	interface.implements(interfaces.IDictionary)

	def __init__(self, lookupPath):
		self.lookupPath = lookupPath

		if os.path.exists(self.lookupPath):
			self.connection = sql.connect(self.lookupPath)
			self.cursor = self.connection.cursor()
		else:
			raise LookupError( 'No path' + self.lookupPath )


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
