#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import base64
import io
import mimetypes
import os
import sys

import logging
logger = logging.getLogger(__name__)

import simplejson as json

from zope import interface
from zope import component
from zope.deprecation import deprecate
from zope.configuration import xmlconfig

import nti.contentrendering
from nti.contentrendering import interfaces
from nti.contentrendering import RenderedBook

interface.moduleProvides( interfaces.IRenderedBookTransformer )

class _JSONPWrapper(object):

	def __init__(self, ntiid, filename, jsonpFunctionName):
		self.filename = filename
		self.jsonpFunctionName = jsonpFunctionName
		self.data = {}
		self.data['ntiid'] = ntiid
		self.data['Content-Type'] = mimetypes.guess_type(filename)[0]
		self.data['version'] = '1'

		# Read the ToC file and base64 encode
		with io.open( filename, 'rb') as file:
			self.data['content'] = base64.standard_b64encode(file.read())
			self.data['Content-Encoding'] = 'base64'

	def writeJSONPToFile(self):
		# Write the JSONP output
		with io.open( self.filename + '.jsonp', 'wb') as file:
			file.write(self.jsonpFunctionName + '(')
			json.dump(self.data, file)
			file.write(');')

def main():
	""" Main program routine """

	contentLocation = sys.argv[1]

	xmlconfig.file( 'configure.zcml', package=nti.contentrendering )
	zope_conf_name = os.path.join( contentLocation, '..', 'configure.zcml' )
	if os.path.exists( zope_conf_name ):
		xmlconfig.file( os.path.abspath( zope_conf_name ), package=nti.contentrendering )

	context = interfaces.JobComponents( os.path.split( os.path.abspath( contentLocation ) )[-1] )

	book = RenderedBook.RenderedBook( None, contentLocation )
	transform( book, context=context )

def transform( book, context=None ):
	"""
	Based on information in the RenderedBook, converts the ToC, content HTML files, and the root icon into 
	a JSONP file for use working around CORS issues.  This transform is non-distructive and will not alter 
	the source files in any way.

	The transform will always return true, because any failures in file IO will raise an IOError exception.
	"""

	# Export the ToC file as a JSONP file
	_JSONPWrapper( book.toc.root_topic.ntiid, book.toc.filename, 'jsonpToc' ).writeJSONPToFile()
	# Export the root icon as a JSONP file if it exists
	if( book.toc.root_topic.has_icon() ):
		_JSONPWrapper( book.toc.root_topic.ntiid, 
			       os.path.join(book.contentLocation, book.toc.root_topic.get_icon()), 
			       'jsonpData' ).writeJSONPToFile()
	# Export the topic HTML files as JSONP files
	_process_topic( book.toc.root_topic, book.contentLocation )

	return True

def _process_topic( topic, contentLocation ):
	"""
	This function will export a topic to JSONP format and then recursively process any child topics.
	The function has no return value.
	"""
	_JSONPWrapper( topic.ntiid, os.path.join(contentLocation, topic.filename), 'jsonpContent' ).writeJSONPToFile()

	# Process any child nodes
	for child in topic.childTopics:
		_process_topic( child, contentLocation )

if __name__ == '__main__':
	main()
