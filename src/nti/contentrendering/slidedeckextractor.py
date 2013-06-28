#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTISlideDeck extractor

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import argparse
import simplejson
import collections

from zope import interface

from nti.contentrendering import interfaces as cr_interfaces

interface.moduleProvides(cr_interfaces.IRenderedBookExtractor)

def get_attribute(node, name):
	attributes = node.attrib if node is not None else {}
	result = attributes.get(name, None)
	return unicode(result) if result else None

def find_objects(topic, mimeType):
	for node in topic.dom(b'object'):
		type_ = get_attribute(node, 'type')
		if type_ == mimeType:
			yield node

def process_ntislidedecks(topic, result):
	for node in topic.dom(b'object').filter(b'.ntislidedeck'):
		d = {u'class': u'ntislidedeck', u'MimeType':u'application/vnd.nextthought.ntislidedeck'}
		for p in node.iterchildren():
			if p.tag == 'param':
				name = get_attribute(p, 'name')
				value = get_attribute(p, 'value')
				if name and value and name not in ('type'):
					d[name.lower()] = value

		_id = d.get('slidedeckid', d.get('ntiid'))
		if _id and _id not in result:
			result[_id] = d
	return result

def process_elements(topic, result, mimeType):
	for node in find_objects(topic, mimeType):
		d = {u'class': mimeType.split('.')[-1], u'MimeType':mimeType}
		ntiid = get_attribute(node, 'data-ntiid')
		if ntiid:
			d[u'ntiid'] = ntiid
		for p in node.iterchildren():
			if p.tag == 'param':
				name = get_attribute(p, 'name')
				value = get_attribute(p, 'value')
				if name and value:
					d[name.lower()] = value

		_id = d.get(u'slidedeckid', d.get(u'ntiid'))
		if ntiid and ntiid not in result:
			result[_id].append(d)
	return result

def process_book(book):
	decks = {}
	slides = collections.defaultdict(list)
	videos = collections.defaultdict(list)
	def _loop(topic):
		process_ntislidedecks(topic, decks)
		process_elements(topic, slides, u'application/vnd.nextthought.slide')
		process_elements(topic, slides, u'application/vnd.nextthought.ntislide')
		process_elements(topic, videos, u'application/vnd.nextthought.ntislidevideo')
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

	return list(decks.values())

def transform(book, outpath=None):
	result = process_book(book)
	outpath = outpath or book.contentLocation
	outpath = os.path.expanduser(outpath)
	outfile = os.path.join(outpath, 'slidedeck_index.json')
	with open(outfile, "wt") as fp:
		simplejson.dump(result, fp, indent=4)

def main():
	from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook, EmptyMockDocument

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
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	contentpath = os.path.expanduser(args.contentpath)
	indexname = os.path.basename(contentpath)
	contentpath = contentpath[:-1] if contentpath.endswith(os.path.sep) else contentpath

	document = EmptyMockDocument()
	document.userdata['jobname'] = indexname
	book = NoConcurrentPhantomRenderedBook(document, contentpath)

	transform(book)

if __name__ == '__main__':
	main()
