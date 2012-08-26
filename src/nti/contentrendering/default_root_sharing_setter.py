#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import io
import os
import sys

import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope import component
from zope.deprecation import deprecate
from zope.configuration import xmlconfig

import nti.contentrendering
from nti.contentrendering import interfaces
from nti.contentrendering import RenderedBook

interface.moduleProvides( interfaces.IRenderedBookTransformer )

DEFAULT_SHARING_GROUP_FILENAME = 'nti-default-root-sharing-group.txt'

def main(args):
	""" Main program routine """

	contentLocation = args[0]

	xmlconfig.file( 'configure.zcml', package=nti.contentrendering )
	zope_conf_name = os.path.join( contentLocation, '..', 'configure.zcml' )
	if os.path.exists( zope_conf_name ):
		xmlconfig.file( os.path.abspath( zope_conf_name ), package=nti.contentrendering )

	context = interfaces.JobComponents( os.path.split( os.path.abspath( contentLocation ) )[-1] )

	book = RenderedBook.RenderedBook( None, contentLocation )
	transform( book, context=context )

def transform( book, save_toc=True, context=None ):
	"""
	Modifies the TOC dom by adding the "shareWith" attribute to the root node.
	"""
	dom = book.toc.dom
	toc = dom.getElementsByTagName("toc")

	if toc and os.path.exists( os.path.join( book.contentLocation, '..', DEFAULT_SHARING_GROUP_FILENAME ) ):
		modified = _handle_toc(toc[0], book)
		if save_toc:
			if modified:
				book.toc.save()
			return modified
		return modified

	raise Exception( "Failed to add default sharing group to  %s. Either the RenderedBook is malformed or the default sharing group data file is missing." % (book) )

def _handle_toc(toc, book):
	contentLocation = book.contentLocation
	modified = True

	if contentLocation:
		sharedWith = ''
		with io.open( os.path.join(contentLocation, '..', DEFAULT_SHARING_GROUP_FILENAME), 'rb') as file:
			for line in file.readlines():
				if line[0] is not '#':
					# Otherwise the line is a comment
					sharedWith = ' '.join([sharedWith, line.strip()])

		index = book.toc.root_topic
		modified = index.set_default_sharing_group( sharedWith.strip() )

	return modified

if __name__ == '__main__':
	main( sys.argv[1:] )
