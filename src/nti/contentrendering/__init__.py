#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pkg_resources import resource_exists, resource_filename

def javascript_path( js_name ):
	"""
	:return: A path to a javascript resource of this package, suitable for passing to phantomjs.
	:raises Exception: If the resource does not exist
	"""
	js_name = 'js/' + js_name
	if not resource_exists( __name__, js_name ):
		raise Exception( "Resource %s not found" % js_name )
	return resource_filename( __name__, js_name )


import warnings
import os
import subprocess
import anyjson as json
import urllib

warnings.warn( "Using whatever phantomjs is on the path" )


_none_key = object()
def run_phantom_on_page( htmlFile, scriptName, args=(), key=_none_key, expect_no_output=False, expect_non_json_output=False ):
	# As of phantomjs 1.4, the html argument must be a URL
	if not htmlFile.startswith( 'file:' ):
		htmlFile = urllib.basejoin( 'file://', urllib.pathname2url( os.path.abspath( htmlFile ) ) )

	# Prior to 1.5, a --load-plugins=no was necessary to prohibit loading
	# plugins, some of which produced console output that screwed our parsing.
	# In 1.6, this is off by default and the arg is gone.

	# TODO: Rewrite the scripts to use the built-in webserver and communicate
	# over a socket as opposed to stdout/stderr? As of 1.6, I think this is the recommended approach

	process = "phantomjs %s %s %s 2>/dev/null" % (scriptName, htmlFile, " ".join([str(x) for x in args]))
	logger.debug( "Executing %s", process )
	# TODO: Rewrite this without the shell for safety and speed
	jsonStr = subprocess.Popen(process, shell=True, stdout=subprocess.PIPE).communicate()[0].strip()
	result = ''
	if expect_no_output:
		if jsonStr:
			raise ValueError( "Process (%s) generated unexpected output (%s)" %(process, jsonStr) )
	elif expect_non_json_output:
		result = jsonStr
	else:
		try:
			try:
				result = json.loads(jsonStr)
			except ValueError:
				if jsonStr:
					__traceback_info__ = htmlFile, scriptName
					# TODO: This should no longer be necessary on 1.6, yes?
					logger.exception( "Got unparseable output. Trying again" )
					# We got output. Perhaps there was plugin junk above? Try
					# again with just the last line.
					result = json.loads( jsonStr.splitlines()[-1] )
				else:
					raise
		except:
			logger.exception( "Failed to read json (%s) from %s", jsonStr, process )
			raise

	if key is _none_key:
		return result

	return (key, result)
