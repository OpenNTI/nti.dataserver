#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import argparse
import io
import os

import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope.configuration import xmlconfig

import nti.contentrendering
from nti.contentrendering import interfaces

interface.moduleProvides( interfaces.IRenderedBookTransformer )

DEFAULT_SHARING_GROUP_FILENAME = 'nti-default-root-sharing-group.txt'

def _parse_args():
	arg_parser = argparse.ArgumentParser( description="Content default sharing setter" )
	arg_parser.add_argument( 'contentpath', help="Content book location" )
	arg_parser.add_argument( "-g", "--groupname", dest='groupname', help="Name of the default sharing group", default=None)
	return arg_parser.parse_args()

def main():
	""" Main program routine """
	from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook, EmptyMockDocument

	args = _parse_args()
	contentpath = os.path.expanduser(args.contentpath)

	xmlconfig.file( 'configure.zcml', package=nti.contentrendering )
	zope_conf_name = os.path.join( contentpath, '..', 'configure.zcml' )
	if os.path.exists( zope_conf_name ):
		xmlconfig.file( os.path.abspath( zope_conf_name ), package=nti.contentrendering )

	context = interfaces.JobComponents( os.path.split( os.path.abspath( contentpath ) )[-1] )

	book = NoConcurrentPhantomRenderedBook( EmptyMockDocument(), contentpath )
	transform( book, context=context, group_name=args.groupname )

def transform( book, save_toc=True, context=None, group_name=None ):
	"""
	Modifies the TOC dom by adding the "shareWith" attribute to the root node.
	"""
	dom = book.toc.dom
	toc = dom.getElementsByTagName("toc")

	if toc and ( group_name or os.path.exists( os.path.join( book.contentLocation, '..', DEFAULT_SHARING_GROUP_FILENAME ) ) ):
		modified = _handle_toc(toc[0], book, group_name=group_name)
		if save_toc:
			if modified:
				book.toc.save()
			return modified
		return modified

	raise Exception( "Failed to add default sharing group to  %s. Either the RenderedBook is malformed or the default sharing group data file is missing." % (book) )

def _handle_toc(toc, book, group_name=None):
	
	modified = True
	contentLocation = book.contentLocation

	if contentLocation:
		sharedWith = []
		if group_name:
			sharedWith.append(group_name)
		else:
			sharedWith_file = os.path.join(contentLocation, '..', DEFAULT_SHARING_GROUP_FILENAME)
			with io.open( sharedWith_file, 'rb') as src:
				for line in src.readlines():
					if line[0] is not '#':
						# Otherwise the line is a comment
						sharedWith.append(line.strip())
		
		sharedWith = ' '.join(sharedWith)
		index = book.toc.root_topic
		modified = index.set_default_sharing_group( sharedWith.strip() )

	return modified

if __name__ == '__main__':
	main()
