#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic whoosh indexer.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import glob

from whoosh import index

from nti.contentindexing.whoosh.spec import WhooshIndexSpec

class BasicWhooshIndexer(object):

	def get_schema(self, name=u''):
		raise NotImplementedError()

	def remove_index_files(self, indexdir, indexname):
		if os.path.exists(indexdir):
			pathname = '%s/*%s*' % (indexdir, indexname)
			for name in glob.glob(pathname):
				try:
					os.remove(name)
				except OSError:
					logger.warn("Cannot remove %s", name)

	def create_index(self, indexdir, indexname):
		if not os.path.exists(indexdir):
			os.makedirs(indexdir)
		ix = index.create_in(indexdir, schema=self.get_schema(), indexname=indexname)
		return ix

	def process_topic(self, idxspec, node, writer, lang='en'):
		raise NotImplementedError()

	def process_book(self, idxspec, writer, lang='en'):
		toc = idxspec.book.toc
		def _loop(topic):
			count = self.process_topic(idxspec, topic, writer, lang)
			for t in topic.childTopics:
				count += _loop(t)
			return count or 0
		docs = _loop(toc.root_topic)
		return docs

	def get_index_name(self, book, indexname=None):
		indexname = indexname or book.jobname
		return unicode(indexname)

	def get_content_path(self, book):
		result = os.path.expanduser(book.contentLocation)
		return result

	def get_index_dir(self, book, indexdir=None):
		content_path = self.get_content_path(book)
		indexdir = indexdir or os.path.join(content_path, "indexdir")
		return unicode(indexdir)

	def get_index_writer(self, index):
		return index.writer(optimize=False, merge=False)
	
	def commit_writer(self, writer):
		writer.commit(optimize=True, merge=True)

	def index(self, book, indexdir=None, indexname=None, optimize=False):
		indexname = self.get_index_name(book, indexname)
		indexdir = self.get_index_dir(book, indexdir)
		self.remove_index_files(indexdir, indexname)
		idxspec = WhooshIndexSpec(content=book, 
								  indexname=indexname, 
								  indexdir=indexdir)

		logger.info('Indexing %s' % indexname)

		idx = self.create_index(indexdir, indexname)
		writer = self.get_index_writer(idx)
		docs = self.process_book(idxspec, writer)

		logger.info("%s total document(s) produced" % docs)

		# commit changes
		self.commit_writer(writer)

		if optimize:  # for testing
			logger.info("Optimizing index")
			idx.optimize()
		logger.info('Indexing %s completed' % indexname)
		return idx, docs

_BasicWhooshIndexer = BasicWhooshIndexer #BWC
