#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Creates an archive for a book assets.

.. $Id$
"""
from __future__ import unicode_literals, print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import os
import glob
import zipfile
import argparse

from zope import interface
from zope import component
from zope.configuration import xmlconfig, config

import nti.contentrendering
from nti.contentrendering.interfaces import IRenderedBookArchiver
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook, EmptyMockDocument

BLACK_LIST = (r'.*\.jsonp', r'indexdir', r'cache-manifest', r'archive\.zip', r'htaccess')
BLACK_LIST_RE = tuple([re.compile(x) for x in BLACK_LIST])

interface.moduleProvides(IRenderedBookArchiver)

def is_black_listed(name):
	for pattern in BLACK_LIST_RE:
		if pattern.match(name):
			return True
	return False

def _archive(source_path, out_dir=None, verbose=False):
	source_path = os.path.expanduser(source_path)
	source_path = source_path + '/' if not source_path.endswith('/') else source_path
	if not os.path.exists(source_path) or not os.path.isdir(source_path):
		raise Exception("Invalid source directory")
	
	added = set()
	out_dir = out_dir or source_path
	out_dir = os.path.expanduser(out_dir)
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)

	outfile = os.path.join(out_dir, 'archive.zip')
	logger.info("Archiving '%s' to '%s'", source_path, outfile)

	zf = zipfile.ZipFile(outfile, mode="w")
	try:
		os.chdir(source_path)
		dname = os.path.basename(source_path[0:-1])

		def _process(path):
			pattern = os.path.join(path, "*")
			for pathname in glob.glob(pattern):
				name = os.path.basename(pathname)
				if is_black_listed(name):
					continue
				if os.path.isdir(pathname):
					_process(pathname)
				else:
					arcname = dname + '/' + pathname[len(source_path):]
					added.add(arcname)
					if verbose:
						print("Adding %s" % arcname)
					zf.write(pathname, arcname=arcname, compress_type=zipfile.ZIP_DEFLATED)
		_process(source_path)
	finally:
		zf.close()

	return added

def archive(book, out_dir=None, verbose=False):
	location = os.path.expanduser(book.contentLocation)
	return _archive(location, out_dir, verbose)

def create_archive(book, out_dir=None, verbose=False, name=u''):
	archiver = component.queryUtility(IRenderedBookArchiver, name=name)
	if archiver is None:
		archiver = component.queryUtility(IRenderedBookArchiver)
	result = archiver.archive(book, out_dir, verbose)
	return result
	
def main():
	context = config.ConfigurationMachine()
	xmlconfig.registerCommonDirectives(context)
	xmlconfig.file("configure.zcml", nti.contentrendering, context=context)

	arg_parser = argparse.ArgumentParser(description="Archive book content")
	arg_parser.add_argument('content_path', help="Book content path")
	arg_parser.add_argument("-o", "--outdir", dest='out_dir', help="Output directory")
	arg_parser.add_argument('-a', '--archiver', dest='archiver', help="The archiver name")
	arg_parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	verbose = args.verbose
	archiver = args.archiver or u''
	content_path = os.path.expanduser(args.content_path)
	jobname = os.path.basename(content_path)
	out_dir = args.out_dir or content_path

	document = EmptyMockDocument()
	document.userdata['jobname'] = jobname
	book = NoConcurrentPhantomRenderedBook(document, content_path)
	create_archive(book, out_dir, verbose, archiver)

if __name__ == '__main__':
	main()
