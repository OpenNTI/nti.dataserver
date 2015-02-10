#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import re
import argparse
import simplejson
from collections import defaultdict

from zope import interface

from nti.contentrendering.utils import EmptyMockDocument
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook

from nti.contentrendering.interfaces import ISlideDeckExtractor
interface.moduleProvides(ISlideDeckExtractor)

def get_attribute(node, name):
	attributes = node.attrib if node is not None else {}
	result = attributes.get(name, None)
	return unicode(result) if result else None

def find_objects(topic, mimeType):
	for node in topic.dom(b'object'):
		type_ = get_attribute(node, 'type')
		if type_ == mimeType:
			yield node

def _store_param(p, data, exclude=()):
	if p.tag == 'param':
		name = get_attribute(p, 'name')
		value = get_attribute(p, 'value')
		if name and value and name not in exclude:
			data[name.lower()] = value

def process_ntislidedecks(topic, result, containers):
	topic_ntiid = getattr(topic, 'ntiid', None) or u''
	for node in topic.dom(b'object').filter(b'.ntislidedeck'):
		d = {u'class': u'ntislidedeck', 
			 u'MimeType':u'application/vnd.nextthought.ntislidedeck'}
		for p in node.iterchildren():
			_store_param(p, d, ('type',))

		iden = d.get('slidedeckid') or d.get('ntiid')
		if iden and iden not in result:
			result[iden] = d
			containers[topic_ntiid].append(d)
	return result

def process_elements(topic, result, mimeType, containers):
	topic_ntiid = getattr(topic, 'ntiid', None) or u''
	for node in find_objects(topic, mimeType):
		clazz_name = mimeType.split('.')[-1]
		d = {u'class': clazz_name, u'MimeType':mimeType}
		ntiid = get_attribute(node, 'data-ntiid') 
		if ntiid:
			d[u'ntiid'] = ntiid
		for p in node.iterchildren():
			_store_param(p, d)

		iden = d.get(u'slidedeckid') or d.get(u'ntiid')
		if ntiid and ntiid not in result:
			result[iden].append(d)
			containers[topic_ntiid].append(d)
	return result

def process_book(book, containers):
	decks = {}
	slides = defaultdict(list)
	videos = defaultdict(list)

	def _loop(topic):
		process_ntislidedecks(topic, decks, containers)
		process_elements(topic, slides,
						 u'application/vnd.nextthought.slide', containers)
		process_elements(topic, slides,
						 u'application/vnd.nextthought.ntislide', containers)
		process_elements(topic, videos, 
						 u'application/vnd.nextthought.ntislidevideo', containers)
		for t in topic.childTopics:
			_loop(t)
	_loop(book.toc.root_topic)

	for sid, deck in decks.items():
		ds = slides.get(sid)
		dv = videos.get(sid)
		if ds is not None:
			deck['Slides'] = list(ds)
		if dv is not None:
			deck['Videos'] = list(dv)

	result = list(decks.values())
	return result

def save_index_file(outpath, data, dom_ntiid):
	items = {}
	containers = {}
	for topic_ntiid, iterable in data.items():
		containers.setdefault(topic_ntiid, [])
		for item in iterable:
			ntiid = item.get(u'ntiid') or item.get(u'slidedeckid')
			if not ntiid:
				continue
			items[ntiid] = item
			containers[topic_ntiid].append(ntiid)

	slide_content_index = {'Items': items, 'Containers':containers}
	filename = 'slide_content_index.json'
	with open(os.path.join(outpath, filename), "wb") as fp:
		simplejson.dump(slide_content_index, fp, indent=4)

	# Write the JSONP version
	with open(os.path.join(outpath, filename + 'p'), "wb") as fp:
		fp.write('jsonpReceiveContent(')
		simplejson.dump({'ntiid': dom_ntiid,
					     'Content-Type': 'application/json',
					     'Content-Encoding': 'json',
					     'content': slide_content_index,
					     'version': '1'}, fp, indent=4)
		fp.write(');')
	
_EMPTY_TEXT = u' '*4
def transform(book, savetoc=True, outpath=None):
	result = []
	dom = book.toc.dom
	containers = defaultdict(list)
	decks = process_book(book, containers)
	
	outpath = outpath or book.contentLocation
	outpath = os.path.expanduser(outpath)
	
	for deck in decks:
		ntiid = deck.get('ntiid')
		if not ntiid: 
			continue

		ntiid = re.sub('[:,\.,/,\*,\?,\<,\>,\|]', '_', ntiid.replace('\\', '_'))
		outfile = os.path.join(outpath, '%s.json' % ntiid)
		with open(outfile, "wt") as fp:
			result.append(outfile)
			simplejson.dump(deck, fp, indent=2)
	
		# separator text node
		node = dom.createTextNode(_EMPTY_TEXT)
		dom.childNodes[0].appendChild(node)
		# create a reference node
		node = dom.createElement('reference')
		node.setAttribute('type', deck.get('MimeType') )
		node.setAttribute('ntiid', deck.get('ntiid') )
		node.setAttribute('href', '%s.json' % ntiid )
		dom.childNodes[0].appendChild(node)
		# separator text node
		node = dom.createTextNode(u'\n')
		dom.childNodes[0].appendChild(node)

	ntiid = dom.childNodes[0].getAttribute('ntiid')
	save_index_file(outpath, containers, ntiid)
	if savetoc:
		book.toc.save()
	return result

def extract(contentpath, outpath=None, jobname=None):
	jobname = jobname or os.path.basename(contentpath)
	document = EmptyMockDocument()
	document.userdata['jobname'] = jobname
	book = NoConcurrentPhantomRenderedBook(document, contentpath)
	return transform(book, outpath)

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

	arg_parser = argparse.ArgumentParser(description="Content indexer")
	arg_parser.add_argument('contentpath', help="Content book location")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", 
							action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	contentpath = os.path.expanduser(args.contentpath)
	jobname = os.path.basename(contentpath)
	contentpath = contentpath[:-1] if contentpath.endswith(os.path.sep) else contentpath
	extract(contentpath, jobname=jobname)

if __name__ == '__main__':
	main()
