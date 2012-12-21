#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import argparse

from zope import interface
from zope import component

from nti.contentrendering import interfaces as cr_interfaces

import logging
logger = logging.getLogger(__name__)

interface.moduleProvides(cr_interfaces.IRenderedBookTransformer )
		
def transform(book, indexdir=None, name=''):
	indexer = component.queryUtility(cr_interfaces.IBookIndexer, name=name)
	if indexer is None:
		indexer = component.getUtility(cr_interfaces.IBookIndexer)
	indexer.index(book, indexdir)
	
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

	arg_parser = argparse.ArgumentParser( description="Content indexer" )
	arg_parser.add_argument( 'contentpath', help="Content book location" )
	arg_parser.add_argument( "-f", "--file_indexing", dest='file_indexing', help="Use file indexing", action='store_true')
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	verbose = args.verbose
	file_indexing = args.file_indexing
	contentpath = os.path.expanduser(args.contentpath)
	indexname = args.indexname or os.path.basename(contentpath)
	contentpath = contentpath[:-1] if contentpath.endswith(os.path.sep) else contentpath
	
	if verbose:
		logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s')
		
	document = EmptyMockDocument()
	document.userdata['jobname'] = indexname
	book = NoConcurrentPhantomRenderedBook(document, contentpath)
	
	name = 'whoosh.file' if file_indexing else indexname
	transform(book, name=name)
	
if __name__ == '__main__':
	main()
