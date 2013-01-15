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


import os
import sys
import urllib
import subprocess
import anyjson as json

import warnings
try:

	warnings.warn( "Using whatever phantomjs is on the PATH; supported version 1.8.0; version found at %s is %s"
				   %(subprocess.check_output(['which', 'phantomjs']).strip(), subprocess.check_output( ['phantomjs', '-v'] ).strip() ),
				   UserWarning, stacklevel=1)
except subprocess.CalledProcessError:
	warnings.warn( "Phantomjs not found on the PATH" )

_none_key = object()
def run_phantom_on_page( htmlFile, scriptName, args=(), key=_none_key, expect_no_output=False, expect_non_json_output=False ):
	# As of phantomjs 1.4, the html argument must be a URL
	if not htmlFile.startswith( 'file:' ):
		htmlFile = urllib.basejoin( 'file://', urllib.pathname2url( os.path.abspath( htmlFile ) ) )

	# TODO: Rewrite the scripts to use the built-in webserver and communicate
	# over a socket as opposed to stdout/stderr? As of 1.6, I think this is the recommended approach

	process = ['phantomjs', scriptName, htmlFile]
	process.extend( args )
	logger.debug( "Executing %s", process )
	# TODO: subprocess.check_output?
	# On OS X, phantomjs produces some output to stderr that's annoying and usually useless,
	# if truly run headless, about CoreGraphics stuff.
	stderr = None
	if sys.platform == 'darwin' and not os.getenv( 'NTI_KEEP_PHANTOMJS_STDERR' ):
		stderr = open( '/dev/null', 'wb' )

	try:
		jsonStr = subprocess.check_output( process, stderr=stderr ).strip() #.Popen(process, stdout=subprocess.PIPE, stderr=stderr).communicate()[0].strip()
	finally:
		if stderr is not None:
			stderr.close()

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

from nti.utils.futures import ConcurrentExecutor
ConcurrentExecutor = ConcurrentExecutor # BWC re-export
