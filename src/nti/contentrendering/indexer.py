#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import os
import re
import sys
import time
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
	attrs = node.attributes
	return attrs['ntiid'].value if attrs.has_key('ntiid') else None

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

def _sanitize_content(text, tokenizer=default_tokenizer):
	# user ds sanitizer
	text = _sanitize_user_html_to_text(text.lower())
	# remove any html (i.e. meta, link) that is not removed
	text = clean_html(text)
	# tokenize words
	words = tokenizer.tokenize(text)
	words = ' '.join(words)
	return words

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
	if txt:
		txt = unicode(txt.strip().lower())
	return txt
	
def _index_book_node(writer, node, tokenizer=default_tokenizer, file_indexing=True):
	title = unicode(node.title)
	ntiid = unicode(node.ntiid)
	content_file = node.location
	logger.info( "Indexing (%s, %s, %s)", os.path.basename(content_file), title, ntiid )
	
	related = _get_related(node.topic)
	
	# find last_modified
	last_modified = time.time()
	for n in node.dom('meta'):
		attributes = n.attrib
		if attributes.get('http-equiv', None) == "last-modified":
			last_modified = _parse_last_modified(attributes.get('content', None))
			break
		
	if file_indexing and os.path.exists(content_file):
		with open(content_file, "r") as f:
			content = f.read()

		content = _get_page_content(content)
		content = _sanitize_content(content)
	else:
		# get content
		content = []
		def _collector(n, lst):
			if not isinstance(n, etree._Comment):
				txt = _get_text(n)
				if txt:
					lst.append(txt)
				for c in n.iterchildren():
					_collector(c, lst)
				
		for n in node.dom("div").filter(".page-contents"):
			_collector(n, content)
	
		content = tokenizer.tokenize(' '.join(content))
		content = unicode(' '.join(content))

	#TODO: find key words
	keywords = set()
	try:
		as_time = datetime.fromtimestamp(float(last_modified))
		writer.add_document(ntiid=unicode(ntiid),
							title=unicode(title),
							content=unicode(content),
							quick=unicode(content),
							related=related,
							keywords=sorted(keywords),
							last_modified=as_time)
	except Exception:
		writer.cancel()
		raise	
	
def transform(book, indexname=None, indexdir=None, recreate_index=True, optimize=True):
	contentPath = book.contentLocation
	indexname = indexname or book.jobname
	if not indexdir:
		indexdir = os.path.join(contentPath, "indexdir")
		
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
	from nti.contentrendering.tests import NoPhantomRenderedBook, EmptyMockDocument
	args = sys.argv[1:]
	if args:
		book = NoPhantomRenderedBook( EmptyMockDocument(), args[0])
		indexname = args[1] if len(args) > 1 else 'MAIN'
		transform(book, indexname=indexname)
	else:
		print("Specify a book location")
