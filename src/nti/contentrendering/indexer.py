#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import os
import re
import sys
import time
import codecs
from datetime import datetime
from xml.dom.minidom import Node

import lxml.etree as etree

from zope import interface

from nltk import clean_html
from nltk.tokenize import RegexpTokenizer

from whoosh import index

from nti.contentrendering import interfaces
from nti.contentfragments.html import _sanitize_user_html_to_text
from nti.contentsearch.whoosh_contenttypes import create_book_schema
from nti.contentrendering.termextract import extract_key_words_from_tokens, TermExtractor

import logging
logger = logging.getLogger(__name__)

interface.moduleProvides( interfaces.IRenderedBookTransformer )

page_c_pattern = re.compile("<div class=\"page-contents\">(.*)</body>")

default_tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*",
									flags = re.MULTILINE | re.DOTALL | re.UNICODE)

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

def _sanitize_content(text, tokens=False, tokenizer=default_tokenizer ):
	# user ds sanitizer
	text = _sanitize_user_html_to_text(text)
	# remove any html (i.e. meta, link) that is not removed
	text = clean_html(text)
	# tokenize words
	tokenized_words = tokenizer.tokenize(text)
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

class _KeyWordFilter(object):

	def __init__(self, single_strength_min_occur=3, max_limit_strength=2):
		self.max_limit_strength = max_limit_strength
		self.single_strength_min_occur = single_strength_min_occur

	def __call__(self, word, occur, strength):
		result = (strength == 1 and occur >= self.single_strength_min_occur) or (strength <= self.max_limit_strength)
		result = result and len(word) > 1
		return result

def _extract_key_words(tokenized_words, extractor=None, max_words=10):
	extractor = extractor or TermExtractor(_KeyWordFilter())
	records = extract_key_words_from_tokens(tokenized_words, extractor=extractor)
	keywords = []
	for r in records[:max_words]:
		word = r.norm
		if r.terms: word = r.terms[0] # pick the first word
		keywords.append(unicode(word.lower()))
	return keywords

def _index_book_node(writer, node, tokenizer=default_tokenizer, file_indexing=False):
	title = unicode(node.title)
	ntiid = unicode(node.ntiid)
	content_file = node.location
	logger.info( "Indexing (%s, %s, %s)", os.path.basename(content_file), title, ntiid )
	
	related = _get_related(node.topic)
	
	# find last_modified
	last_modified = time.time()
	for n in node.dom(b'meta'):
		attributes = n.attrib
		if attributes.get('http-equiv', None) == "last-modified":
			last_modified = _parse_last_modified(attributes.get('content', None))
			break
	
	as_time = datetime.fromtimestamp(float(last_modified))
	def _to_index(content, keywords=()):
		if not content:
			return
		
		try:
			content = unicode(content.lower())
			writer.add_document(ntiid=ntiid,
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
		tokenized_words = _sanitize_content(raw_content, tokens=True)
		documents.append(tokenized_words)
	else:
		# get content
		def _collector(n):
			if not isinstance(n, etree._Comment):
				content = _get_node_content(n)
				if content:
					tokenized_words = tokenizer.tokenize(content)
					documents.append(tokenized_words)
					
				for c in n.iterchildren():
					_collector(c)
				
		for n in node.dom(b'div').filter(b'.page-contents'):
			_collector(n)
	
	# TODO: key word should done on a book basis
	# compute keywords
	all_words = []
	for tokenized_words in documents:
		all_words.extend(tokenized_words)
	keywords = _extract_key_words(all_words)
	logger.debug("\tkeywords %s", keywords )
	
	for tokenized_words in documents:
		content = ' '.join(tokenized_words)
		_to_index(content, keywords)
		
def transform(book, indexname=None, indexdir=None, recreate_index=True, optimize=True):
	contentPath = book.contentLocation
	indexname = indexname or book.jobname
	if not indexdir:
		indexdir = os.path.join(contentPath, "indexdir")
		
	logger.info('indexing %s(%s)' % (indexname, indexdir))
	
	idx = get_or_create_index(indexdir, indexname, recreate=recreate_index)
	writer = idx.writer(optimize=False, merge=False)
	
	toc = book.toc
	def _loop(topic):
		_index_book_node(writer, topic)
		for t in topic.childTopics:
			_loop(t)			
	_loop(toc.root_topic)
	
	writer.commit(optimize=False, merge=False)
	
	if optimize:
		logger.info( "Optimizing index" )
		idx.optimize()

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s')
	from nti.contentrendering.tests import NoPhantomRenderedBook, EmptyMockDocument
	args = sys.argv[1:]
	if args:
		book = NoPhantomRenderedBook( EmptyMockDocument(), args[0])
		indexname = args[1] if len(args) > 1 else 'MAIN'
		transform(book, indexname=indexname)
	else:
		print("Specify a book location")
