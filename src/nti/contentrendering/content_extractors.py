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

from .render_document import parse_tex
from .interfaces import IRenderedBookExtractor
from .utils import NoConcurrentPhantomRenderedBook

def transform(book, savetoc=False, outpath=None):
	for name, extractor in sorted(component.getUtilitiesFor(IRenderedBookExtractor)):
		logger.info("Extracting %s/%s", name, extractor)
		extractor.transform(book, savetoc=savetoc, outpath=outpath)

def main():
	arg_parser = argparse.ArgumentParser(description="Run content extractor")
	arg_parser.add_argument('contentpath', help="Path to tex content file")
	arg_parser.add_argument('-t', '--toc', help="Save objects in toc",
							action='store_true', dest='savetoc')
	arg_parser.add_argument('-o', '--out', help="Output directoty", dest='outpath')
	arg_parser.add_argument('-v', '--verbose', help="Be verbose",
							action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	# process arguments
	contentpath = os.path.expanduser(args.contentpath)
	if not os.path.exists(contentpath) or os.path.isdir(contentpath):
		raise IOError("Invalid content file")
	
	outpath = os.path.expanduser(args.outpath)
	if outpath and not os.path.exists(outpath):
		raise IOError("Invalid output directory")

	verbose = args.verbose
	savetoc = args.savetoc
	if verbose:
		ei = '[%(asctime)-15s] [%(name)s] %(levelname)s: %(message)s'
		logging.basicConfig(level=logging.DEBUG, format=ei)

	# do extraction
	document = parse_tex(contentpath, perform_transforms=False)
	book = NoConcurrentPhantomRenderedBook(document, contentpath)
	transform(book, savetoc=savetoc, outpath=outpath)

if __name__ == '__main__':
	main()
