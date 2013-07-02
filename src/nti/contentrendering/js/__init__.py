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
import urlparse
import subprocess
import contextlib
import anyjson as json

import warnings
try:

	warnings.warn( "Using whatever phantomjs is on the PATH; supported version 1.9.0; version found at %s is %s"
				   %(subprocess.check_output(['which', 'phantomjs']).strip(), subprocess.check_output( ['phantomjs', '-v'] ).strip() ),
				   UserWarning, stacklevel=1)
except subprocess.CalledProcessError:
	warnings.warn( "Phantomjs not found on the PATH" )

class _PhantomProducedUnexpectedOutputError(subprocess.CalledProcessError):

	def __str__(self):
		return "Command '%s' produced unexpected output '%s'" % (self.cmd, self.output)

class _closing(contextlib.closing):
	"A None-safe closing contextmanager"
	def __exit__( self, *exc_info ):
		if self.thing is not None:
			self.thing.close()

_none_key = object()
def run_phantom_on_page( htmlFile, scriptName, args=(), key=_none_key, expect_no_output=False, expect_non_json_output=False ):
	"""
	Execute a phantom JS script against an HTML file; returns the result of that script
	as either a JSON object or a byte string (if ``expect_non_json_output`` is set to True).

	:param str htmlFile: The URL (usually ``file://``) to the HTML file on which
		to run the script. Also can be a regular path on Unix.
	:param str scriptName: The regular absolute path to the JavaScript
		file to run.
	:keyword args: A sequence of arguments to pass to the script.
	:keyword key: An arbitrary object. If one is provided, then the return
		value of this function will be a tuple consisting of the key
		and what otherwise would have been returned. This assists in
		correlating parallel runs of this function.
	:keyword expect_no_output: If set to ``True``, this function will
		verify that script execution created no output on stdout, and return None.

	:raises subprocess.CalledProcessError: If the process fails to return a 0 exit code,
		or if ``expect_no_output`` is set to True and output is created on stdout.
	:raises ValueError: If JSON decoding fails.
	:raises TypeError: If JSON decoding fails.
	"""
	# As of phantomjs 1.4, the html argument must be a URL
	if urlparse.urlparse( htmlFile ).scheme not in ('file', 'http', 'https'):
		# assume they gave a path. The explicit use of schemes is to
		# help with windows, where a path like "c:\foo\bar" gets a scheme of 'c'
		htmlFile = urllib.basejoin( 'file://', urllib.pathname2url( os.path.abspath( htmlFile ) ) )

	# TODO: Rewrite the scripts to use the built-in webserver and communicate
	# over a socket as opposed to stdout/stderr? As of 1.6, I think this is the recommended approach

	process = ['phantomjs', scriptName, htmlFile]
	process.extend( args )
	__traceback_info__ = process
	logger.debug( "Executing %s", process )

	# On OS X, phantomjs produces some output to stderr that's annoying and usually useless,
	# if truly run headless, about CoreGraphics stuff. Since we often expect output on stdout,
	# we cannot simply direct it there.
	stderr = None
	if sys.platform == 'darwin' and not os.getenv( 'NTI_KEEP_PHANTOMJS_STDERR' ):
		stderr = open( '/dev/null', 'wb' )

	with _closing(stderr):
		jsonStr = subprocess.check_output( process, stderr=stderr ).strip()
		__traceback_info__ += (jsonStr,)


	if expect_no_output:
		if jsonStr:
			raise _PhantomProducedUnexpectedOutputError(0, process, jsonStr)
		return None

	result = None
	if expect_non_json_output:
		result = jsonStr
	else:
		if not jsonStr:
			raise ValueError( "Expected JSON output, but no stdout generated." )

		try:
			result = json.loads(jsonStr)
		except ValueError:
			logger.debug( "Got unparseable output. Trying again", exc_info=True )
			# We got output. Perhaps there was plugin junk above? Try
			# again with just the last line.
			# This often happens if the console log methods are used; unfortunately,
			# phantom seems to have no way to direct those to stderr
			result = json.loads( jsonStr.splitlines()[-1] )

	if key is _none_key:
		return result

	return (key, result)

from nti.utils.futures import ConcurrentExecutor
ConcurrentExecutor = ConcurrentExecutor # BWC re-export
