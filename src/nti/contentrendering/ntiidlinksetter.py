#!/usr/bin/env python
# $Id$
import os
import urllib
import sys

from pyquery import PyQuery
from . import RenderedBook

import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope import component
from zope.deprecation import deprecate
from . import interfaces

interface.moduleProvides( interfaces.IRenderedBookTransformer )

def transform( book, save_toc=True ):

	def modify_hrefs_in_topic( topic ):
		result = 0
		hrefs = ()
		dom = topic.dom

		if dom:
			hrefs = dom("a['href']") #Any need to do the next/prev links in the header?

		for href in hrefs:
			filename = href.attrib['href']
			if filename.startswith( topic.get_topic_filename() ):
				# Leave in-page links alone so as not to confuse the browser
				continue

			fragment = ''
			if '#' in filename:
				filename, fragment = filename.split( '#', 1 )
				fragment = '#' + fragment
			ntiid_topic = book.toc.root_topic.topic_with_filename( filename )
			if ntiid_topic:
				href.attrib['href'] = ntiid_topic.ntiid # + fragment # When the dataserver can deal with stripping fragments, add these back
				result += 1

		if result:
			topic.write_dom()
		# recurse
		for t in topic.childTopics:
			result += modify_hrefs_in_topic( t )
		return result

	return modify_hrefs_in_topic( book.toc.root_topic )
