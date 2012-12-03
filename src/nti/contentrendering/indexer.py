#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import re
import glob
import time
import codecs
import hashlib
import argparse
from datetime import datetime
from xml.dom.minidom import Node

import lxml.etree as etree

from zope import interface

from nltk import clean_html

from whoosh import index

from nti.contentprocessing import split_content
from nti.contentprocessing import interfaces as cp_interfaces
from nti.contentprocessing import get_content_translation_table
from nti.contentprocessing.termextract import term_extract_key_words

from nti.contentfragments.html import _sanitize_user_html_to_text

from nti.contentrendering import interfaces

from nti.contentsearch.whoosh_contenttypes import create_book_schema

import logging
logger = logging.getLogger(__name__)

interface.moduleProvides( interfaces.IRenderedBookTransformer )

page_c_pattern = re.compile("<div class=\"page-contents\">(.*)</body>")

def get_schema():
	return create_book_schema()

def get_or_create_index(indexdir, indexname, recreate=True):

	if not os.path.exists(indexdir):
		os.makedirs(indexdir)
		recreate = True

	if not index.exists_in(indexdir, indexname=indexname):
		recreate = True

	if recreate:
		ix = index.create_in(indexdir, schema=get_schema(), indexname=indexname)
	else:
		ix = index.open_dir(indexdir, indexname=indexname)

	return ix

def _get_ntiid(node):
	attrs = node.attributes if node is not None else None
	return attrs['ntiid'].value if attrs and attrs.has_key('ntiid') else None

def _add_ntiid_to_set(pset, node):
	ntiid = _get_ntiid(node)
	if ntiid:
		pset.add(unicode(ntiid))
	return pset

def _get_related(node):
	"""
	return a list w/ the related nttids for this node
	"""
	related = set()
	if node is  not None:
		for child in node.childNodes:
			if child.nodeType == Node.ELEMENT_NODE:
				if child.localName == 'topic':
					_add_ntiid_to_set(related, child)
				elif child.localName == 'Related':
					for c in child.childNodes:
						if c.nodeType == Node.ELEMENT_NODE and c.localName == 'page':
							_add_ntiid_to_set(related, c)

	result = list(related)
	result.sort()

	return result

def _parse_text(text, pattern, default=''):
	m = pattern.search(text, re.M|re.I)
	return m.groups()[0] if m else default

def _get_page_content(text):
	c = text.replace('\n','')
	c = c.replace('\r','')
	c = c.replace('\t','')
	c = _parse_text(c, page_c_pattern, None)
	return c or text

def _sanitize_content(text, tokens=False, table=None):
	# user ds sanitizer
	text = _sanitize_user_html_to_text(text)
	# remove any html (i.e. meta, link) that is not removed
	text = clean_html(text)
	# tokenize words
	text = text.translate(table) if table else text
	tokenized_words = split_content(text)
	result = tokenized_words if tokens else ' '.join(tokenized_words)
	return result

def _parse_last_modified(t):
	result = time.time()
	try:
		if t:
			ms = ".0"
			idx = t.rfind(".")
			if idx != -1:
				ms = t[idx:]
				t = t[0:idx]

			t = time.strptime(t,"%Y-%m-%d %H:%M:%S")
			t = long(time.mktime(t))
			result = str(t) + ms
	except:
		pass	
	return float(result)

def _get_text(node):
	txt = node.text
	txt = unicode(txt.strip()) if txt else u''
	return txt

def _get_tail(node):
	txt = node.tail
	txt = unicode(txt.strip()) if txt else u''
	return txt

def _get_node_content(node):
	result = [_get_text(node), _get_tail(node)]
	result = ' '.join(result)
	return result.strip()

@interface.implementer( cp_interfaces.ITermExtractFilter)
class _KeyWordFilter(object):

	def __init__(self, single_strength_min_occur=3, max_limit_strength=2):
		self.max_limit_strength = max_limit_strength
		self.single_strength_min_occur = single_strength_min_occur

	def __call__(self, word, occur, strength):
		result = (strength == 1 and occur >= self.single_strength_min_occur) or (strength <= self.max_limit_strength)
		result = result and len(word) > 1
		return result

def _extract_key_words(tokenized_words, max_words=10):
	records = term_extract_key_words(tokenized_words, "indexer")
	keywords = []
	for r in records[:max_words]:
		word = r.norm
		if r.terms: word = r.terms[0] # pick the first word
		keywords.append(unicode(word.lower()))
	return keywords

def _get_attribute(node, name):
	attributes = node.attrib
	return attributes.get(name, None)

def _index_book_node(writer, node, file_indexing=False):
	title = unicode(node.title)
	ntiid = unicode(node.ntiid)
	content_file = node.location
	logger.info( "Indexing (%s, %s, %s)", os.path.basename(content_file), title, ntiid )
	
	related = _get_related(node.topic)
	table = get_content_translation_table()
	
	# find last_modified
	last_modified = time.time()
	for n in node.dom(b'meta'):
		if _get_attribute(n, 'http-equiv') == "last-modified":
			last_modified = _parse_last_modified(_get_attribute(n, 'content'))
			break
	
	as_time = datetime.fromtimestamp(float(last_modified))
	def _to_index(docid, content, keywords=()):
		if not content:
			return
		
		docid = "%r %s" % (ntiid, docid)
		docid = unicode(hashlib.md5(docid).hexdigest())
		try:
			content = unicode(content)
			writer.add_document(#docid=docid,
								ntiid=ntiid,
								title=title,
								content=content,
								quick=content,
								related=related,
								keywords=keywords,
								last_modified=as_time)
		except Exception:
			writer.cancel()
			raise	
			
	documents = []
	if file_indexing and os.path.exists(content_file):
		with codecs.open(content_file, "r", encoding='UTF-8') as f:
			raw_content = f.read()

		raw_content = _get_page_content(raw_content)
		tokenized_words = _sanitize_content(raw_content, tokens=True, table=table)
		if tokenized_words:
			documents.append(tokenized_words)
	else:
		# get content
		def _collector(n, data):
			if not isinstance(n, etree._Comment):
				content = _get_node_content(n)
				content = content.translate(table) if content else None
				if content:
					tokenized_words = split_content(content)
					data.extend(tokenized_words)
					
				for c in n.iterchildren():
					_collector(c, data)
				
		def _traveler(n):
			n_id = _get_attribute(n, "id")
			data_ntiid = _get_attribute(n, "data_ntiid")
			if n_id or (data_ntiid and data_ntiid != "none"):
				data = []
				_collector(n, data)
				documents.append(data)
			else:
				content = _get_node_content(n)
				content = content.translate(table) if content else None
				if content:
					tokenized_words = split_content(content)
					documents.append(tokenized_words)
				
				for c in n.iterchildren():
					_traveler(c)
		
		for n in node.dom(b'div').filter(b'.page-contents'):
			_traveler(n)
			
		for n in node.dom(b'div').filter(b'#footnotes'):
			_traveler(n)
	
	# TODO: key word should done on a book basis
	# compute keywords
	all_words = []
	for tokenized_words in documents:
		all_words.extend(tokenized_words)
	keywords = _extract_key_words(all_words)
	logger.debug("\tkeywords %s", keywords )
	
	for docid, tokenized_words in enumerate(documents):
		content = ' '.join(tokenized_words)
		_to_index(docid, content, keywords)
		
def transform(book, indexname=None, indexdir=None, recreate_index=True, optimize=True, file_indexing=False):
	contentPath = book.contentLocation
	indexname = indexname or book.jobname
	if not indexdir:
		indexdir = os.path.join(contentPath, "indexdir")
		
	logger.info('indexing %s(%s)' % (indexname, indexdir))
	
	idx = get_or_create_index(indexdir, indexname, recreate=recreate_index)
	writer = idx.writer(optimize=False, merge=False)
	
	toc = book.toc
	def _loop(topic):
		_index_book_node(writer, topic, file_indexing=file_indexing)
		for t in topic.childTopics:
			_loop(t)			
	_loop(toc.root_topic)
	
	writer.commit(optimize=False, merge=False)
	
	if optimize:
		logger.info( "Optimizing index" )
		idx.optimize()

def _remove_index_files(location, indexname):
	indexdir = os.path.join(location, "indexdir") 
	if os.path.exists(indexdir):
		pathname = '%s/*%s*' % (indexdir, indexname)
		for name in glob.glob(pathname):
			os.remove(name)

def main():
	
	def register():
		from zope.configuration import xmlconfig
		from zope.configuration.config import ConfigurationMachine
		from zope.configuration.xmlconfig import registerCommonDirectives
		context = ConfigurationMachine()
		registerCommonDirectives(context)
		
		import nti.contentrendering as contentrendering
		xmlconfig.file("configure.zcml", contentrendering, context=context)
	register()

	arg_parser = argparse.ArgumentParser( description="Content indexer" )
	arg_parser.add_argument( 'contentpath', help="Content book location" )
	arg_parser.add_argument( "-i", "--indexname", dest='indexname', help="Content index name", default=None)
	arg_parser.add_argument( "-f", "--file_indexing", dest='file_indexing', help="Use file indexing", action='store_true')
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	contentpath = os.path.expanduser(args.contentpath)
	contentpath = contentpath[:-1] if contentpath.endswith(os.path.sep) else contentpath
	indexname = args.indexname or os.path.basename(contentpath)
	verbose = args.verbose
	file_indexing = args.file_indexing
	if verbose:
		logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s')
		
	_remove_index_files(contentpath, indexname)
	
	from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook, EmptyMockDocument
	
	book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), contentpath)
	transform(book, indexname=indexname, file_indexing=file_indexing)
	
if __name__ == '__main__':
	main()
