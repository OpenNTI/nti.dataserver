#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content indexer.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import argparse

from zope import interface
from zope import component

from nti.contentrendering import interfaces as cr_interfaces

_type_map = { 'book': cr_interfaces.IBookIndexer,
			  'audio': cr_interfaces.IAudioTranscriptIndexer,
			  'video': cr_interfaces.IVideoTranscriptIndexer,
			  'nticard': cr_interfaces.INTICardIndexer }

def transform(book, iface=cr_interfaces.IBookIndexer, name=''):
	name = name or u''
	indexer = component.queryUtility(iface, name=name)
	if indexer is None:
		indexer = component.getUtility(iface)
	indexer.index(book)

@interface.implementer(cr_interfaces.IRenderedBookIndexer)
class BookIndexer(object):
	def transform(self, book, name=''):
		transform(book, cr_interfaces.IBookIndexer, name=name)

@interface.implementer(cr_interfaces.IRenderedBookIndexer)
class NTICardIndexer(object):
	def transform(self, book, name=''):
		transform(book, cr_interfaces.INTICardIndexer, name=name)

@interface.implementer(cr_interfaces.IRenderedBookIndexer)
class AudioTrancriptIndexer(object):
	def transform(self, book, name=''):
		transform(book, cr_interfaces.IAudioTranscriptIndexer, name=name)

@interface.implementer(cr_interfaces.IRenderedBookIndexer)
class VideoTrancriptIndexer(object):
	def transform(self, book, name=''):
		transform(book, cr_interfaces.IVideoTranscriptIndexer, name=name)

def main():
	from nti.contentrendering.utils import EmptyMockDocument
	from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook
	
	def register():
		from zope.configuration import xmlconfig
		from zope.configuration.config import ConfigurationMachine
		from zope.configuration.xmlconfig import registerCommonDirectives
		context = ConfigurationMachine()
		registerCommonDirectives(context)

		import nti.contentrendering as contentrendering
		xmlconfig.file("configure.zcml", contentrendering, context=context)

	# parse arguments
	arg_parser = argparse.ArgumentParser(description="Content Transcript indexer")
	arg_parser.add_argument('contentpath', help="Content book location")
	arg_parser.add_argument('-n' '--name', help="Indexer name", dest='name')
	arg_parser.add_argument('-t', '--type',
							dest='type',
							choices=_type_map,
							default='book',
							help="The content type to index")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose",
							action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	# process arguments
	contentpath = os.path.expanduser(args.contentpath)
	contentpath = contentpath[:-1] if contentpath.endswith(os.path.sep) else contentpath
	jobname = os.path.basename(contentpath)

	verbose = args.verbose
	name = args.name or jobname
	indexer = _type_map[args.type]
	if not os.path.exists(contentpath) or not os.path.isdir(contentpath):
		raise IOError("Invalid content directory")

	if verbose:
		import logging
		ei = '%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s'
		logging.basicConfig(level=logging.DEBUG, format=ei)

	# register zcml
	register()

	# do indexing
	document = EmptyMockDocument()
	document.userdata['jobname'] = jobname
	book = NoConcurrentPhantomRenderedBook(document, contentpath)
	transform(book, iface=indexer, name=name)

if __name__ == '__main__':
	main()
