#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dictionary generation

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import gzip
import cPickle
import argparse

import xml.sax
from xml.sax.handler import ContentHandler

# The pywikipedia dist has both a wiktionary package and a wiktionary module
# one seems to be a duplicate of the other, not sure which is canonical
# When installed with distutils, only the wiktionary module gets compiled and packaged
# which means this is a class, not a sub-module. It's weird.
from pywikipedia.wiktionary import WiktionaryPage

marker_langs = {
		'en': '==English==',
		'ru': '= {{-ru-}} =',
		# unmarked
		'be': 'Belarusian',
		'ca': 'Catalan',
		'da': 'Danish',
		'de': 'German',
		'eo': 'Esperanto',
		'et': 'Estonian',
		'el': 'Greek',
		'es': 'Spanish',
		'fi': 'Finnish',
		'fr': 'French',
		'gl': 'Galician',
		'hu': 'Hungarian',
		'is': 'Icelandic',
		'it': 'Italian',
		'lt': 'Lithuanian',
		'nl': 'Dutch',
		'no': 'Norwegian',
		'pl': 'Polish',
		'pt': 'Portuguese',
		'ro': 'Romanian',
		'sk': 'Slovakian',
		'sl': 'Slovenian',
		'sv': 'Swedish',
		'th': 'Thai',
		'uk': 'Ukrainian' }

class Wiktionary(object):

	dictName = 'dictionary.bin.gz'
	indexName = 'dictionary.index.gz'

	index = {}
	dictFile = None

	def __init__(self, location):
		self.location = location
		self.__loadDict()

	def __loadDict(self):
		indexPath = os.path.join(self.location, self.indexName)
		if not os.path.exists(indexPath):
			return

		indexFile = gzip.open(os.path.join(self.location, self.indexName), 'rb')
		self.index = cPickle.load(indexFile)
		indexFile.close()

		dictPath = os.path.join(self.location, self.dictName)
		if os.path.exists(dictPath):
			self.dictFile = dictPath
		else:
			self.index = {}
			self.dictFile = None

	def generateDictionary(self, wiktionaryDump, lang='en'):
		if not os.path.isdir(self.location):
			os.makedirs(self.location)

		dict_file = gzip.open(os.path.join(self.location, self.dictName), 'wb')
		try:
			parser = xml.sax.make_parser()
			parser.setContentHandler(WiktionaryDumpHandler(self.index, dict_file, lang))
			dump = open(wiktionaryDump)
			parser.parse(dump)
			dump.close()
		finally:
			dict_file.close()

		indexFile = gzip.open(os.path.join(self.location, self.indexName), 'wb')
		try:
			cPickle.dump(self.index, indexFile)
		finally:
			indexFile.close()
		self.__loadDict()

	def lookupWord(self, term):
		result = None
		location = self.index.get(term, None)
		if location is not None:
			dictionary = gzip.open(self.dictFile, 'rb')
			try:
				dictionary.seek(location)
				result = cPickle.load(dictionary)
			finally:
				dictionary.close()
		return result

class WiktionaryDumpHandler(ContentHandler):

	page = 0
	entry = 0

	def __init__(self, index, dictionary, lang='en'):
		ContentHandler.__init__(self)  # Not a new-style class :(
		self.lang = lang
		self.index = index
		self.dictionary = dictionary

		self.name = []
		self.nameLabel = 'title'
		self.insideName = False

		self.markup = []
		self.markupLabel = 'text'
		self.insideMarkup = False

		self.pageLabel = 'page'
		self.insidePage = False
		self.text_marker = marker_langs[self.lang].lower()

	def startElement(self, localname, attrs):
		if localname == self.pageLabel:
			self.page += 1
			self.insidePage = True
		elif localname == self.nameLabel:
			self.name = []
			self.insideName = True
		elif localname == self.markupLabel:
			self.markup = []
			self.insideMarkup = True

	def endElement(self, localname):
		markup = u''.join(self.markup)
		name = u''.join(self.name).strip()
		if localname == self.pageLabel:
			self.insidePage = False
		elif localname == self.nameLabel:
			self.insideName = False
			# In the event that its not a word (based on the title) set that we are
			# out of the page so we don't collect wikimarkup
			if name.find(':') > -1:
				self.name = []
				self.insidePage = False
		elif self.insidePage and localname == self.markupLabel:
			self.insideMarkup = False
			self.persistEntry(name, markup)

	def persistEntry(self, title, text):
		if text.lower().find(self.text_marker) >= 0:
			self.entry += 1
			title = title.encode("utf-8")
			location = self.dictionary.tell()
			self.index[title] = location
			page = WiktionaryPage(self.lang, title)
			page.parseWikiPage(text)
			cPickle.dump(page, self.dictionary)
			print('Found %s,entry=%d,page=%d' % (title.decode("utf-8"), self.entry, self.page))

	def characters(self, data):
		if self.insidePage and self.insideName:
			self.name.append(data)
		elif self.insidePage and self.insideMarkup:
			self.markup.append(data)

def main(args=None):

	_lang_map = {x:x for x in marker_langs.keys()}
	_action_map = {'generate': 0, 'lookup': 1 }

	arg_parser = argparse.ArgumentParser(description="Dictionary generation")
	arg_parser.add_argument('location', help="The path location")
	arg_parser.add_argument('-a', '--action',
							 dest='action',
							 choices=_action_map,
							 help="The action to perform",
							 default='generate')
	arg_parser.add_argument('-w', '--word',
							 dest='word',
							 help="The word to lookup")
	arg_parser.add_argument('-x', '--xml',
							 dest='wiki',
							 help="The xml wiki file")
	arg_parser.add_argument('-l', '--language',
							 dest='lang',
							 choices=_lang_map,
							 help="The language",
							 default='en')

	args = arg_parser.parse_args(args=args)
	wiki = Wiktionary(args.location)

	if args.action == 'generate':
		assert args.wiki, 'must provide a xml wiki dump file'
		wiki.generateDictionary(args.wiki, args.lang)
	elif args.action == 'lookup':
		assert args.word, 'must provide a word'
		response = wiki.lookupWord(args.word)
		if response:
			meanings = response.entries[args.lang].getMeanings()
			for et, entries in meanings.items():
				print(et)
				for entry in entries:
					print("\t", entry.definition)
		else:
			print ('Not found')

if __name__ == '__main__':
	main()
