#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTI card indexer.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger(__name__)

import os
import argparse

from zope import interface
from zope import component

from nti.contentrendering import interfaces as cr_interfaces

interface.moduleProvides(cr_interfaces.IRenderedBookIndexer)

def transform(book, name='', indexdir=None):
	name = name or u''
	indexer = component.queryUtility(cr_interfaces.INTICardIndexer, name=name)
	if indexer is None:
		indexer = component.getUtility(cr_interfaces.INTICardIndexer)
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

	arg_parser = argparse.ArgumentParser(description="NTI card indexer")
	arg_parser.add_argument('contentpath', help="Content book location")
	arg_parser.add_argument('-i' '--indexer', help="Indexer name", dest='indexer')
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	verbose = args.verbose
	indexer = args.indexer or u''
	contentpath = os.path.expanduser(args.contentpath)
	jobname = os.path.basename(contentpath)
	contentpath = contentpath[:-1] if contentpath.endswith(os.path.sep) else contentpath

	if verbose:
		logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s')

	document = EmptyMockDocument()
	document.userdata['jobname'] = jobname
	book = NoConcurrentPhantomRenderedBook(document, contentpath)

	transform(book, name=indexer)

if __name__ == '__main__':
	main()
