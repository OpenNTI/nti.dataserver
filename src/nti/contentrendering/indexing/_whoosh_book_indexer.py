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

from nti.contentsearch import interfaces as search_interfaces

from . import _node_utils as node_utils
from . import _termextract as termextract
from . import _content_utils as content_utils
from . import interfaces as cridxr_interfaces
from ._common_indexer import _BasicWhooshIndexer

@interface.implementer(cridxr_interfaces.IWhooshBookIndexer)
class _WhooshBookIndexer(_BasicWhooshIndexer):

	def get_schema(self, name='en'):
		creator = component.getUtility(search_interfaces.IWhooshBookSchemaCreator, name=name)
		return creator.create()

	def add_document(self, writer, docid, ntiid, title, content,
					 related=(), keywords=(), last_modified=None):

		docid = unicode(docid) if docid else None
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

	def _get_last_modified(self, node):
		last_modified = time.time()
		for n in node.dom(b'meta'):
			if node_utils.get_attribute(n, 'http-equiv') == "last-modified":
				value = node_utils.get_attribute(n, 'content')
				last_modified = content_utils.parse_last_modified(value)
				break

		last_modified = last_modified or time.time()
		last_modified = datetime.fromtimestamp(float(last_modified))
		return last_modified

class _IdentifiableNodeWhooshIndexer(_WhooshBookIndexer):
	"""
	Indexing topic children nodes that either have an id or data_ntiid attribute
	"""

	def process_topic(self, idxspec, node, writer, language='en'):
		title = unicode(node.title)
		ntiid = unicode(node.ntiid)
		content_file = node.location

		logger.info("Indexing Node (%s, %s, %s)", os.path.basename(content_file), title, ntiid)

		table = get_content_translation_table(language)
		related = node_utils.get_related(node.topic)
		last_modified = self._get_last_modified(node)

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
		keywords = termextract.extract_key_words(all_words)

		count = 0
		for docid, tokenized_words in documents:
			content = ' '.join(tokenized_words)
			self.add_document(writer, docid, ntiid, title, content, related, keywords, last_modified)
			count += 1
		logger.info("%s document(s) produced" % count)
		return count

class _BookFileWhooshIndexer(_WhooshBookIndexer):
	"""
	Index each topic (file) as a whole. 1 inndex document per topic
	"""

	page_c_pattern = re.compile("<div class=\"page-contents\">(.*)</body>")

	def _parse_text(self, text, pattern, default=''):
		m = pattern.search(text, re.M | re.I)
		return m.groups()[0] if m else default

	def _get_page_content(self, text):
		c = re.sub('[\n\t\r]', '', text)
		m = self.page_c_pattern.search(c, re.M | re.I)
		c = m.groups()[0] if m else u''
		return c or text

	def process_topic(self, idxspec, node, writer, language='en'):
		title = unicode(node.title)
		ntiid = unicode(node.ntiid)
		content_file = node.location

		logger.info("Indexing File (%s, %s, %s)", os.path.basename(content_file), title, ntiid)

		table = get_content_translation_table(language)
		related = node_utils.get_related(node.topic)
		last_modified = self._get_last_modified(node)

		result = 0
		if os.path.exists(content_file):
			with codecs.open(content_file, "r", encoding='UTF-8') as f:
				raw_content = f.read()

			raw_content = self._get_page_content(raw_content)
			tokenized_words = content_utils.sanitize_content(raw_content, tokens=True, table=table)
			if tokenized_words:
				result = 1
				content = ' '.join(tokenized_words)
				keywords = termextract.extract_key_words(tokenized_words)
				self.add_document(writer, ntiid, ntiid, title, content, related, keywords, last_modified)

		return result

_DefaultWhooshBookIndexer = _BookFileWhooshIndexer
