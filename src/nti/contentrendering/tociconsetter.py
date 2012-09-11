#!/usr/bin/env python
from __future__ import print_function, unicode_literals
import os
import sys

from . import RenderedBook

import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope import component
from zope.deprecation import deprecate
from zope.configuration import xmlconfig

import nti.contentrendering
from . import interfaces

interface.moduleProvides( interfaces.IRenderedBookTransformer )

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
	Modifies the TOC dom by: reading NTIIDs out of HTML content and adding them
	to the TOC, setting icon attributes in the TOC. Also modifies HTML content
	to include background images when appropriate.
	"""
	dom = book.toc.dom
	toc = dom.getElementsByTagName("toc")
	if toc:
		modified, child_nodes = _handle_toc(toc[0], book, save_toc, context=context)
		if save_toc:
			if modified:
				book.toc.save()
			return modified
		# Testing mode: return a tuple
		return modified, child_nodes

	raise Exception( "Failed to transform %s" % (book) )

def _handle_toc(toc, book, save_dom, context=None):
	contentLocation = book.contentLocation
	attributes = toc.attributes
	if not attributes.has_key('href'):
		logger.warn( "Assuming index.html for root node in %s", book )
		attributes['href'] = "index.html"
	modified = True
	# For testing, we return the child nodes we modify
	# (otherwise don't waste the memory)
	child_nodes = []
	if contentLocation:
		index = book.toc.root_topic
		modified = index.set_ntiid()

		title = index.get_title( )
		if title:
			modified = index.set_label( title ) or modified
			if os.path.exists( os.path.join(contentLocation, "icons/chapters/" + title + "-icon.png" ) ):
				modified = index.set_icon( "icons/chapters/" + title + "-icon.png" ) or modified
			else:
				modified = index.set_icon( "icons/chapters/generic_book.png" ) or modified

		for node in index.childTopics:
			node.save_dom = save_dom
			_handle_topic( book, node, context=context )
			if not save_dom: child_nodes.append( node )

	return modified, child_nodes

def _query_finder( book, topic, iface, context=None ):
	# If nothing for the job, query the global default. This should be handled
	# by our customized components implementation
	result = component.queryMultiAdapter( (book,topic), iface, context=context )
	return result

def _handle_topic( book, _topic, context=None ):
	modified = False

	if _topic.is_chapter():
		if not _topic.has_icon():
			icon_finder = _query_finder( book, _topic, interfaces.IIconFinder, context=context )
			icon_path = icon_finder.find_icon() if icon_finder else None
			modified = _topic.set_icon( icon_path ) if icon_path else modified

		modified = _topic.set_ntiid() or modified
		bg_finder = _query_finder( book, _topic, interfaces.IBackgroundImageFinder, context=context )
		bg_path = bg_finder.find_background_image() if bg_finder else None
		modified |= _topic.set_background_image( bg_path ) if bg_path else modified

		# modify the sub-topics
		modified = _handle_sub_topics(_topic) or modified

	return modified

def _handle_sub_topics(topic):
	"""
	Set the NTIID for all sub topics
	"""

	modified = False

	for node in topic.childTopics:
		modified = node.set_ntiid() or modified

	return modified

@interface.implementer(interfaces.IIconFinder)
@component.adapter(interfaces.IRenderedBook,interfaces.IEclipseMiniDomTopic)
class SimpleConventionIconFinder(object):
	"""
	Follows a simple convention to find icons for topics: looks in the
	'icons/chapters' directory for a file named 'CX.png', where 'X' is the
	chapter (topic) number.
	"""
	path_type = 'icons'

	def __init__( self, book, topic ):
		self._book = book
		self._topic = topic

	def find_icon( self ):
		# Note that the return is in URL-space using /, but the check
		# for existence uses local path conventions
		imagename = 'C' + str(self._topic.ordinal) + '.png'

		path = os.path.join( self._book.contentLocation,
							 self.path_type,
							 'chapters',
							 imagename )
		if os.path.exists( path ):
			return self.path_type + '/chapters/' + imagename

@interface.implementer_only(interfaces.IBackgroundImageFinder)
@component.adapter(interfaces.IRenderedBook,interfaces.IEclipseMiniDomTopic)
class SimpleConventionBackgroundImageFinder(SimpleConventionIconFinder):
	"""
	Just like the super class, but looks in the 'images/chapters' directory.
	"""
	path_type = 'images'
	find_background_image = SimpleConventionIconFinder.find_icon

if __name__ == '__main__':
	main( sys.argv[1:] )
