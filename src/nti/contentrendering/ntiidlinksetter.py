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
			hrefs = []
			# The main body
			hrefs.extend( dom("a['href']") )
			# next/prev/up links in the header
			for rel in ('next','up','prev'):
				hrefs.extend( dom( 'link[href][rel='+rel+']' ) )

		for href in hrefs:
			filename = href.attrib['href']
			if filename == '#':
				# We're probably dealing with a javascript onclick handler here,
				# ignore it
				continue
			if filename.startswith( '#' ):
				# Yay, it's already an in-page relative link and we can
				# ignore it. (See comments below)
				continue
			if filename.startswith( 'tag:nextthought' ):
				# Yay, it's already a NTIID
				# Note that we're not using the nti.dataserver.ntiids module to validate this to
				# avoid dependencies (which may not be important)
				continue

			fragment = ''
			filename_frag = filename.split( '#', 1 )
			if len(filename_frag) == 2:
				filename, fragment = filename_frag
				fragment = '#' + fragment

			if filename == topic.get_topic_filename():
				if fragment:
					# Make in-page links drop all references to a file for consistency.
					# A fragment-only link is correctly handled by the browser
					href.attrib['href'] = fragment
					result += 1
				else:
					# Bare links to the current page occur as part of some referencing
					# schemes. (E.g., "Problem number <Section>.<Counter>" generates
					# two links, one for the current page, one for the counter.) The first
					# link is useless and annoying if you click it, so make it do
					# nothing (But this doesn't count as real work)
					logger.debug( "Stripping a bare link to the current page '%s' in %s", href.attrib['href'], topic )
					href.attrib['href'] = '#'
				continue


			ntiid_topic = book.toc.root_topic.topic_with_filename( filename )
			if ntiid_topic:
				# Fragments are not sent when the browser follows a URL, so
				# the client will have to handle fragment behaviour
				href.attrib['href'] = ntiid_topic.ntiid + fragment
				result += 1
			else:
				logger.warning( "Unable to resolve NTIID for href '%s' and file '%s' in %s", href.attrib['href'], filename, topic )

		if result:
			topic.write_dom()
		# recurse
		for t in topic.childTopics:
			result += modify_hrefs_in_topic( t )
		return result

	return modify_hrefs_in_topic( book.toc.root_topic )
