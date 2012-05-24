#!/usr/bin/env python

import os
import re
import sys
import time

from datetime import datetime
from xml.dom.minidom import parse
from xml.dom.minidom import Node

from whoosh import index

from concurrent.futures import ThreadPoolExecutor
from nti.contentsearch.whoosh_contenttypes import create_book_schema

import whoosh.writing
import multiprocessing

from nltk import clean_html
from nltk.tokenize import RegexpTokenizer

import logging
logger = logging.getLogger(__name__)

# -----------------------------

name_anchor_pattern = re.compile(".+[#a\d+]$")
ref_pattern = re.compile("<span class=\"ref\">(.*)</span>")
last_m_pattern = re.compile("<meta content=\"(.*)\" http-equiv=\"last-modified\"")
page_c_pattern = re.compile("<div class=\"page-contents\">(.*)</body>")
default_tokenizer = RegexpTokenizer(r"(?x)([A-Z]\.)+ | \$?\d+(\.\d+)?%? | \w+([-']\w+)*", flags = re.MULTILINE | re.DOTALL) 

scope_pattern = re.compile(r'<(\w).*name="(.*)".*itemscope.*itemtype="http://schema.org/CreativeWork".*>',\
							   re.MULTILINE | re.DOTALL)
	
prop_pattern = re.compile(r'<(\w).*itemprop="(.*)".*>', re.MULTILINE | re.DOTALL)
	
# -----------------------------

def get_schema():
	return create_book_schema()

def get_or_create_index(indexdir, indexname ='prealgebra', recreate = True):

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

# -----------------------------

def get_ntiid(node):
	attrs = node.attributes
	return attrs['ntiid'].value if attrs.has_key('ntiid') else None

def get_title(node):
	attrs = node.attributes
	return attrs['label'].value if attrs.has_key('label') else None

def add_ntiid_to_set(pset, node):
	ntiid = get_ntiid(node)
	if ntiid:
		pset.add(unicode(ntiid))
	return pset

def get_related(node):
	"""
	return a list w/ the related nttids for this node
	"""

	related = set()
	for child in node.childNodes:
		if child.nodeType == Node.ELEMENT_NODE:
			if child.localName == 'topic':
				add_ntiid_to_set(related, child)
			elif child.localName == 'Related':
				for c in child.childNodes:
					if c.nodeType == Node.ELEMENT_NODE and c.localName == 'page':
						add_ntiid_to_set(related, c)

	result = list(related)
	result.sort()
	return result

def parse_text(text, pattern, defValue=''):
	m = pattern.search(text, re.M|re.I)
	if m:
		return m.groups()[0]
	else:
		return defValue

def get_last_modified(text):
	"""
	return the last modified date from the text
	"""
	now = time.time()

	t = parse_text(text, last_m_pattern, None)
	try:
		if t:
			ms = ".0"
			idx = t.rfind(".")
			if idx != -1:
				ms = t[idx:]
				t = t[0:idx]

			t = time.strptime(t,"%Y-%m-%d %H:%M:%S")
			t = long(time.mktime(t))
			f = str(t) + ms
			return f
		else:
			return now
	except:
		return now

def get_ref(text):
	"""
	return the reference [chapter/section] code
	"""
	return parse_text(text, ref_pattern)

def get_page_content(text):
	"""
	Returns everything after <div class="page-contents">
	"""
	c = text.replace('\n','')
	c = c.replace('\r','')
	c = c.replace('\t','')
	c = parse_text(c, page_c_pattern, None)
	return c or text

def word_splitter(text, tokenizer=default_tokenizer):
	"""
	remove all html related tags and returs a list of words
	"""
	text = clean_html(text.lower())
	words = tokenizer.tokenize(text)
	return words

def get_first_paragraph(text):
	"""
	Get the first paragraph with text in the specified content"
	"""
	s = re.sub("<p>","\n<p>", text)
	hits = re.findall("<p>.*", s)
	for p in hits:
		content = word_splitter(p)
		content = ' '.join(content)
		if len(content) > 0:
			return content
	return ''

# -----------------------------

class _Node(object):
	def __init__(self, tag, name, level):
		self.tag = tag
		self.level = level
		self.children = []
		self.properties = []
		self.name = unicode(name)

	def __str__(self):
		return "<%s,%s,%s>" % ( self.level, self.name, self.properties )
	
	def __repr__(self):
		return self.__str__()
	
	def add_property(self, value):
		self.properties.append(unicode(value.lower()))
		
def _peek(stack):
	return stack[len(stack) -1] if stack else None

def _pop(stack, result):
	node = stack.pop()
	result.append(node)
	if stack: 
		_peek(stack).children.append(node)
			
def get_microdata(html, sort=True):
	"""
	returns the NTI provide microdata from the specified html string
	"""	
	level = 0
	scopes = []
	objects = []
	
	idx = 0
	length = len(html)
	element = []
	while idx < length:
		if html[idx] == '<' or html[idx] == '>':
			if element:
				if html[idx] == '>':
					element.append(html[idx])	
					tag = ''.join(element).strip()
					element = []
				else:
					element.append('>')
					tag = ''.join(element).strip()
					element = [html[idx]]
									
				if not tag.startswith("</"):
					level = level + 1
					
					sg = scope_pattern.search(tag)
					if sg:
						scopes.append( _Node(sg.groups()[0], sg.groups()[1], level) )
					else:
						m = prop_pattern.search(tag)
						if m and scopes:
							_peek(scopes).add_property(m.groups()[1])
							
					if tag.endswith("/>"):
						if sg:
							_pop(scopes, objects)
							
						level = level - 1
				else:
					if scopes and _peek(scopes).level == level:
						_pop(scopes, objects)
						
					level = level - 1
			else:
				element.append(html[idx])
				
		elif element:
			element.append(html[idx])
			
		idx = idx + 1 
		
	# check if there are left overs
	while scopes:
		_pop(scopes, objects)
	
	if sort:
		objects.sort( key=lambda n: n.level) 
	
	result = []
	for node in objects:
		result.append( (node.name, node.properties) )
		
	return result
		
# -----------------------------

def _index_node(writer, node, contentPath, optimize=False):
	"""
	Index a the information for a toc node
	"""

	attributes = node.attributes
	fileName = str(attributes['href'].value)
	if name_anchor_pattern.match(fileName): # file name ends with an anchor id
		return
	
	content_file = os.path.join(contentPath, str(fileName))
	if not os.path.exists(content_file):
		logger.error("content file '%s' does not exists", content_file)
		return
		
	title = get_title(node)
	ntiid = get_ntiid(node)

	if not ntiid:
		return

	related = get_related(node)
	
	logger.info( "Indexing (%s, %s, %s)", fileName, title, ntiid )

	with open(content_file, "r") as f:
		rawContent = f.read()

	section = get_ref(rawContent)
	last_modified = get_last_modified(rawContent)

	pageRawContent = get_page_content(rawContent)
	content = ' '.join(word_splitter(pageRawContent))

	keywords = set()
	for _, properties in get_microdata(rawContent):
		keywords.update(properties)
		
	try:
		as_time = datetime.fromtimestamp(float(last_modified))
		writer.add_document(ntiid=unicode(ntiid),
							title=unicode(title),
							content=unicode(content),
							quick=unicode(content),
							related=related,
							section=unicode(section),
							keywords=sorted(keywords),
							last_modified=as_time)
	except Exception:
		logger.exception( "Cannot index %s", content_file )
		writer.cancel()
		raise

def get_nodes(tocFile):
	dom = parse(tocFile)
	result = list()

	tocs = dom.getElementsByTagName("toc") # index
	if tocs and len(tocs) > 0:
		result.append(tocs[0])
		for topic in dom.getElementsByTagName("topic"):
			result.append(topic)

	return result

# -----------------------------

def main(tocFile, 
		 contentPath=None,
		 indexdir=None,
		 indexname=None, 
		 recreate_index=True, 
		 optimize=True):
	""" 
	Main program routine
	"""

	if not contentPath:
		contentPath = os.path.dirname(tocFile)
		
	if not indexdir:
		indexdir = os.path.join(contentPath, "indexdir")
		
	indexname = indexname or "prealgebra"
	
	nodes = get_nodes(tocFile)
	idx = get_or_create_index(indexdir, indexname, recreate=recreate_index)

	writer = whoosh.writing.BufferedWriter( idx,
											period=None,
											limit=100,
											commitargs={'optimize' : False, 'merge': False})
	
	with ThreadPoolExecutor(multiprocessing.cpu_count()) as pool:
		for node in nodes:
			pool.submit( _index_node, writer, node, contentPath)

	writer.commit()
	
	if optimize:
		logger.info( "Optimizing index" )
		idx.optimize()

index_content = main

if __name__ == '__main__':
	def _call_main():
		args = sys.argv[1:]
		if args and len(args) >= 1:

			lm = lambda x,i: x[i] if len(x) > i else None
			toc_file = lm(args, 0)
			content_path = lm(args, 1)
			index_directory = lm(args, 2)
			index_name = lm(args, 3)

			main(toc_file, content_path, index_directory, index_name)
		else:
			print "Specify a toc-file [chapter-path] [index-directory] [index-name]"
	_call_main()


