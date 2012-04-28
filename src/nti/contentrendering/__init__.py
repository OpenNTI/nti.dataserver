from __future__ import unicode_literals, print_function
import io
from pkg_resources import resource_exists, resource_filename

from nti.utils.minidom import minidom_writexml # re-export

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
import logging
logger = logging.getLogger(__name__)
warnings.warn( "Using whatever phantomjs is on the path" )
_none_key = object()
def run_phantom_on_page( htmlFile, scriptName, args=(), key=_none_key, expect_no_output=False, expect_non_json_output=False ):
	# phantomjs 1.3 will take plain paths to open, 1.4 requires a URL
	# This is a pretty lousy way to get a URL and probably has escaping problems
	if not htmlFile.startswith( 'file:' ):
		htmlFile = 'file://' + os.path.abspath( htmlFile )
	# They claim that loading plugins is off by default, but that doesn't
	# seem to be true. And some plugins produce output during the loading process,
	# which screws up or JSON parsing. Worse, an unloadable plugin can crash the
	# entire process. So we attempt to force disable plugin loading: However, this
	# is not entirely reliable; there seems to be a race condition. We try instead
	# to parse just the last line
	# NOTE: This problem is fixed with 1.5, which seems to be backwards compatible entirely

	process = "phantomjs --load-plugins=no %s %s %s 2>/dev/null" % (scriptName, htmlFile, " ".join([str(x) for x in args]))
	logger.debug( "Executing %s", process )
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
