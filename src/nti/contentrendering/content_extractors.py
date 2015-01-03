#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import logging
import argparse

from zope import component
from zope.configuration import xmlconfig, config

import nti.contentrendering
from nti.contentrendering.utils import EmptyMockDocument
from nti.contentrendering.interfaces import IRenderedBookExtractor
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook

def transform(book, savetoc=False):
	for name, extractor in sorted(component.getUtilitiesFor(IRenderedBookExtractor)):
		logger.info("Extracting %s/%s", name, extractor)
		extractor.transform(book, savetoc=savetoc)

def main():
	context = config.ConfigurationMachine()
	xmlconfig.registerCommonDirectives(context)
	xmlconfig.file("configure.zcml", nti.contentrendering, context=context)
	
	# parse arguments
	arg_parser = argparse.ArgumentParser(description="Run content extractor")
	arg_parser.add_argument('contentpath', help="Content book location")
	arg_parser.add_argument('-t', '--toc', help="Save objects in toc",
							action='store_true', dest='savetoc')
	arg_parser.add_argument('-v', '--verbose', help="Be verbose",
							action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	# process arguments
	contentpath = os.path.expanduser(args.contentpath)
	contentpath = contentpath[:-1] if contentpath.endswith(os.path.sep) else contentpath
	jobname = os.path.basename(contentpath)

	verbose = args.verbose
	savetoc = args.savetoc
	if not os.path.exists(contentpath) or not os.path.isdir(contentpath):
		raise IOError("Invalid content directory")

	if verbose:
		ei = '%(asctime)-15s %(name)-5s %(levelname)-8s %(message)s'
		logging.basicConfig(level=logging.DEBUG, format=ei)

	# do extraction
	document = EmptyMockDocument()
	document.userdata['jobname'] = jobname
	book = NoConcurrentPhantomRenderedBook(document, contentpath)
	transform(book, savetoc=savetoc)

if __name__ == '__main__':
	main()
