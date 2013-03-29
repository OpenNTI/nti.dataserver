# -*- coding: utf-8 -*-
"""
Basic whoosh indexer.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import glob

from whoosh import index

class _BasicWhooshIndexer(object):

	def get_schema(self, name=u''):
		raise NotImplementedError()

	def remove_index_files(self, indexdir, indexname):
		if os.path.exists(indexdir):
			pathname = '%s/*%s*' % (indexdir, indexname)
			for name in glob.glob(pathname):
				os.remove(name)

	def create_index(self, indexdir, indexname):
		if not os.path.exists(indexdir):
			os.makedirs(indexdir)
		ix = index.create_in(indexdir, schema=self.get_schema(), indexname=indexname)
		return ix

	def process_topic(self, book, node, writer, language='en'):
		raise NotImplementedError()

	def process_book(self, book, writer, language='en'):
		toc = book.toc
		def _loop(topic):
			count = self.process_topic(book, topic, writer, language)
			for t in topic.childTopics:
				count += _loop(t)
			return count
		docs = _loop(toc.root_topic)
		return docs

	def get_index_name(self, book, indexname=None):
		indexname = indexname or book.jobname
		return indexname

	def get_content_path(self, book):
		result = os.path.expanduser(book.contentLocation)
		return result

	def get_index_dir(self, book, indexdir=None):
		content_path = self.get_content_path(book)
		indexdir = indexdir or os.path.join(content_path, "indexdir")
		return indexdir

	def index(self, book, indexdir=None, indexname=None, optimize=True):
		indexname = self.get_index_name(book, indexname)
		indexdir = self.get_index_dir(book, indexdir)
		self.remove_index_files(indexdir, indexname)

		logger.info('Indexing %s(%s)' % (indexname, indexdir))

		idx = self.create_index(indexdir, indexname)
		writer = idx.writer(optimize=False, merge=False)
		docs = self.process_book(book, writer)

		logger.info("%s total document(s) produced" % docs)

		# commit changes
		writer.commit(optimize=False, merge=False)

		if optimize:  # for testing
			logger.info("Optimizing index")
			idx.optimize()

		return idx
