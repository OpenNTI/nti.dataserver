#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh book indexers.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import re
import isodate
import codecs
from datetime import datetime

import lxml.etree as etree

from zope import component
from zope import interface

from nti.contentprocessing import tokenize_content
from nti.contentprocessing import get_content_translation_table

from nti.contentrendering import ConcurrentExecutor

from nti.contentsearch.interfaces import IWhooshBookSchemaCreator

from ._utils import get_related
from ._utils import get_attribute
from ._utils import get_node_content

from ._extract import extract_key_words

from .interfaces import IWhooshBookIndexer

from .content_utils import sanitize_content

from .common_indexer import BasicWhooshIndexer

# global helper functions

etree_Comment = getattr(etree, '_Comment')

def _get_last_modified(node):
	last_modified = None
	for n in node.dom(b'meta'):
		if get_attribute(n, 'http-equiv') == "last-modified":
			last_modified = get_attribute(n, 'content')
			break

	if last_modified is not None:
		__traceback_info__ = last_modified
		try:
			last_modified = isodate.parse_datetime(last_modified)
		except ValueError:
			# Hmm...re-indexing old content?
			last_modified = None

	last_modified = last_modified or datetime.utcnow()
	return last_modified

class _DataNode(object):

	__slots__ = ('title', 'ntiid', 'location', 'related', 'last_modified', 'content',
				 'keywords')

	def __init__(self, node):
		self.location = node.location
		self.content = self.keywords = None
		self.title = unicode(node.title) or u''
		self.ntiid = unicode(node.ntiid) or u''
		self.related = get_related(node.topic)
		self.last_modified = _get_last_modified(node)

	def is_processed(self):
		return self.content or self.keywords

	def __str__(self):
		return "(%s,%s, %s)" % (os.path.basename(self.location), self.title, self.ntiid)

# Base whoosh indexer

@interface.implementer(IWhooshBookIndexer)
class WhooshBookIndexer(BasicWhooshIndexer):

	def get_schema(self, name='en'):
		creator = \
			component.getUtility(IWhooshBookSchemaCreator, name=name)
		return creator.create()

	def add_document(self, writer, docid, ntiid, title, content,
					 related=(), keywords=(), last_modified=None):

		docid = unicode(docid) if docid else u''
		try:
			content = unicode(content)
			writer.add_document(docid=docid,
								ntiid=ntiid,
								title=title,
								content=content,
								quick=content,
								related=related,
								keywords=keywords,
								last_modified=last_modified)
		except Exception:
			writer.cancel()
			raise

_WhooshBookIndexer = WhooshBookIndexer #BWC

# Indexing topic children nodes that either have an id or data_ntiid attribute

class IdentifiableNodeWhooshIndexer(WhooshBookIndexer):

	def process_topic(self, idxspec, node, writer, lang='en'):
		data = _DataNode(node)
		logger.debug("Indexing Node %s", data)

		table = get_content_translation_table(lang)
		documents = []

		def _collector(n, data):
			if not isinstance(n, etree_Comment):
				content = get_node_content(n)
				content = content.translate(table) if content else None
				if content:
					tokenized_words = tokenize_content(content, lang)
					data.extend(tokenized_words)

				for c in n.iterchildren():
					_collector(c, data)

		def _traveler(n):
			n_id = get_attribute(n, "id")
			data_ntiid = get_attribute(n, "data_ntiid")
			if n_id or (data_ntiid and data_ntiid != "none"):
				data = []
				_collector(n, data)
				_id = data_ntiid or n_id
				documents.append((_id, data))
			else:
				content = get_node_content(n)
				content = content.translate(table) if content else None
				if content:
					tokenized_words = tokenize_content(content, lang)
					documents.append((None, tokenized_words))

				for c in n.iterchildren():
					_traveler(c)

		for n in node.dom(b'div').filter(b'.page-contents'):
			_traveler(n)

		for n in node.dom(b'div').filter(b'#footnotes'):
			_traveler(n)

		all_words = []
		for tokenized_words in documents:
			all_words.extend(tokenized_words[1])
		data.keywords = extract_key_words(all_words, lang=lang)

		count = 0
		for docid, tokenized_words in documents:
			data.content = ' '.join(tokenized_words)
			self.add_document(writer, docid, data.ntiid, data.title, data.content,
							  data.related, data.keywords, data.last_modified)
			count += 1
		logger.info("%s document(s) produced" % count)
		return count

_IdentifiableNodeWhooshIndexer = IdentifiableNodeWhooshIndexer #BWC

# Index each topic (file) as a whole. 1 index document per topic

page_c_pattern = re.compile("<div class=\"page-contents\">(.*)</body>")

def _get_page_content(text):
	c = re.sub('[\n\t\r]', '', text)
	m = page_c_pattern.search(c, re.M | re.I)
	c = m.groups()[0] if m else u''
	return c or text

def _process_datanode(node, lang='en'):
	content_file = node.location
	__traceback_info__ = content_file, lang, node
	logger.debug("Processing File %s", node)

	if os.path.exists(content_file):
		with codecs.open(content_file, "r", encoding='UTF-8') as f:
			raw_content = f.read()

		table = get_content_translation_table(lang)
		raw_content = _get_page_content(raw_content)
		tokenized_words = sanitize_content(raw_content, table=table,
										   tokens=True, lang=lang)
		if tokenized_words:
			node.content = ' '.join(tokenized_words)
			node.keywords = extract_key_words(tokenized_words, lang=lang)
	return node

class BookFileWhooshIndexer(WhooshBookIndexer):

	def _index_datanode(self, node, writer, lang='en'):
		result = 0
		if node.is_processed():
			result = 1
			self.add_document(writer, node.ntiid, node.ntiid, node.title, node.content,
							  node.related, node.keywords, node.last_modified)
		return result

	def process_topic(self, idxspec, node, writer, lang='en'):
		data = _DataNode(node)
		data = _process_datanode(data, lang)
		result = self._index_datanode(data, writer, lang)
		return result

	def process_book(self, idxspec, writer, lang='en'):
		# collect nodes to index
		nodes = []
		files = set()
		def _loop(topic):
			data = _DataNode(topic)
			if data.location not in files:
				nodes.append(data)
			files.add(data.location)
			for t in topic.childTopics:
				_loop(t)
		_loop(idxspec.book.toc.root_topic)

		# process and index nodes
		docs = 0
		with ConcurrentExecutor() as executor:
			langs = [lang] * len(nodes)
			for node in executor.map(_process_datanode, nodes, langs):
				if isinstance(node,Exception):
					raise node
				docs += self._index_datanode(node, writer, lang)
		return docs

_BookFileWhooshIndexer = _DefaultWhooshBookIndexer = BookFileWhooshIndexer
