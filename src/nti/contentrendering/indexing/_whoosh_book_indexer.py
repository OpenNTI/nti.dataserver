# -*- coding: utf-8 -*-
"""
Whoosh book indexers.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import re
import time
import codecs
from datetime import datetime

import lxml.etree as etree

from zope import component
from zope import interface

from nti.contentprocessing import split_content
from nti.contentprocessing import get_content_translation_table

from nti.contentrendering import ConcurrentExecutor

from nti.contentsearch import interfaces as search_interfaces

from . import _node_utils as node_utils
from . import _termextract as termextract
from . import _content_utils as content_utils
from . import interfaces as cridxr_interfaces
from ._common_indexer import _BasicWhooshIndexer

# global helper functions

def _get_last_modified(node):
	last_modified = time.time()
	for n in node.dom(b'meta'):
		if node_utils.get_attribute(n, 'http-equiv') == "last-modified":
			value = node_utils.get_attribute(n, 'content')
			last_modified = content_utils.parse_last_modified(value)
			break

	last_modified = last_modified or time.time()
	last_modified = datetime.fromtimestamp(float(last_modified))
	return last_modified

class _DataNode(object):

	__slots__ = ('title', 'ntiid', 'location', 'related', 'last_modified', 'content', 'keywords')

	def __init__(self, node):
		self.location = node.location
		self.content = self.keywords = None
		self.title = unicode(node.title) or u''
		self.ntiid = unicode(node.ntiid) or u''
		self.last_modified = _get_last_modified(node)
		self.related = node_utils.get_related(node.topic)

	def is_processed(self):
		return self.content or self.keywords

	def __str__(self):
		return "(%s,%s, %s)" % (os.path.basename(self.location), self.title, self.ntiid)

# Base whoosh indexer

@interface.implementer(cridxr_interfaces.IWhooshBookIndexer)
class _WhooshBookIndexer(_BasicWhooshIndexer):

	def get_schema(self, name='en'):
		creator = component.getUtility(search_interfaces.IWhooshBookSchemaCreator, name=name)
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

# Indexing topic children nodes that either have an id or data_ntiid attribute

class _IdentifiableNodeWhooshIndexer(_WhooshBookIndexer):

	def process_topic(self, idxspec, node, writer, language='en'):
		data = _DataNode(node)
		logger.debug("Indexing Node %s", data)

		table = get_content_translation_table(language)
		documents = []

		def _collector(n, data):
			if not isinstance(n, etree._Comment):
				content = node_utils.get_node_content(n)
				content = content.translate(table) if content else None
				if content:
					tokenized_words = split_content(content)
					data.extend(tokenized_words)

				for c in n.iterchildren():
					_collector(c, data)

		def _traveler(n):
			n_id = node_utils.get_attribute(n, "id")
			data_ntiid = node_utils.get_attribute(n, "data_ntiid")
			if n_id or (data_ntiid and data_ntiid != "none"):
				data = []
				_collector(n, data)
				_id = data_ntiid or n_id
				documents.append((_id, data))
			else:
				content = node_utils.get_node_content(n)
				content = content.translate(table) if content else None
				if content:
					tokenized_words = split_content(content)
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
		data.keywords = termextract.extract_key_words(all_words)

		count = 0
		for docid, tokenized_words in documents:
			data.content = ' '.join(tokenized_words)
			self.add_document(writer, docid, data.ntiid, data.title, data.content,
							  data.related, data.keywords, data.last_modified)
			count += 1
		logger.info("%s document(s) produced" % count)
		return count

# Index each topic (file) as a whole. 1 index document per topic

page_c_pattern = re.compile("<div class=\"page-contents\">(.*)</body>")

def _get_page_content(text):
	c = re.sub('[\n\t\r]', '', text)
	m = page_c_pattern.search(c, re.M | re.I)
	c = m.groups()[0] if m else u''
	return c or text

def _process_datanode(node, language='en'):
	content_file = node.location
	logger.debug("Processing File %s", node)

	if os.path.exists(content_file):
		with codecs.open(content_file, "r", encoding='UTF-8') as f:
			raw_content = f.read()

		table = get_content_translation_table(language)
		raw_content = _get_page_content(raw_content)
		tokenized_words = content_utils.sanitize_content(raw_content, table=table, tokens=True)
		if tokenized_words:
			node.content = ' '.join(tokenized_words)
			node.keywords = termextract.extract_key_words(tokenized_words)
	return node

class _BookFileWhooshIndexer(_WhooshBookIndexer):

	def _index_datanode(self, node, writer, language='en'):
		result = 0
		if node.is_processed():
			result = 1
			self.add_document(writer, node.ntiid, node.ntiid, node.title, node.content,
							  node.related, node.keywords, node.last_modified)
		return result

	def process_topic(self, idxspec, node, writer, language='en'):
		data = _DataNode(node)
		data = _process_datanode(data, language)
		result = self._index_datanode(data, writer, language)
		return result

	def process_book(self, idxspec, writer, language='en'):
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
			langs = [language] * len(nodes)
			for node in executor.map(_process_datanode, nodes, langs):
				docs += self._index_datanode(node, writer, language)
		return docs

_DefaultWhooshBookIndexer = _BookFileWhooshIndexer
