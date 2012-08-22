#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import base64
import io
import json
import mimetypes
import os
import sys

from nti.contentrendering import RenderedBook

import logging
logger = logging.getLogger(__name__)

from zope import interface
from zope import component
from zope.deprecation import deprecate
from zope.configuration import xmlconfig

import nti.contentrendering
from nti.contentrendering import interfaces

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

def transform( book, context=None ):
	"""
	Modifies the TOC dom by: reading NTIIDs out of HTML content and adding them
	to the TOC, setting icon attributes in the TOC. Also modifies HTML content
	to include background images when appropriate.
	"""

	_process_toc( book.toc )
	_process_topic( book.toc.root_topic, book.contentLocation )

def _process_toc( toc ):
	data = {}
	data['ntiid'] = toc.root_topic.ntiid
	data['Content-Type'] = mimetypes.guess_type(toc.filename)[0]
	data['version'] = '1'

	# Read the ToC file and base64 encode
	with io.open( toc.filename, 'r') as file:
		data['content'] = base64.standard_b64encode(file.read().encode('utf8'))
		data['Content-Encoding'] = 'base64'

	# Write the JSONP output
	with io.open( toc.filename + '.jsonp', 'w') as file:
		file.write('jsonpToc(' + json.dumps(data) + ');')

def _process_topic( topic, contentLocation ):
	data = {}
	data['ntiid'] = topic.ntiid
	data['Content-Type'] = mimetypes.guess_type(topic.filename)[0]
	data['version'] = '1'

	# Read the content file and base64 encode
	with io.open( os.path.join(contentLocation, topic.filename), 'r') as file:
		data['content'] = base64.standard_b64encode(file.read().encode('utf8'))
		data['Content-Encoding'] = 'base64'

	# Write the JSONP output
	with io.open( os.path.join(contentLocation, topic.filename + '.jsonp'), 'w') as file:
		file.write('jsonpContent(' + json.dumps(data) + ');')

	# Process any child nodes
	for child in topic.childTopics:
		_process_topic( child, contentLocation )

if __name__ == '__main__':
	main( sys.argv[1:] )
