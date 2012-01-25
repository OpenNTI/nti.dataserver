from __future__ import unicode_literals, print_function
import io
from pkg_resources import resource_exists, resource_filename

def minidom_writexml(document, outfile):
	"""
	Papers over some very bad Unicode issues
	that crop up with xml.dom.minidom.
	"""
	class _StupidIOPackageCannotDealWithBothStrAndUnicodeObjects(object):
		def __init__( self, under ):
			self._under = under
		def write( self, x ):
			if isinstance( x, str ):
				x = unicode(x)
			self._under.write( x )
	with io.open(outfile, "w", encoding='utf-8') as f:
		document.writexml(_StupidIOPackageCannotDealWithBothStrAndUnicodeObjects(f),
						  encoding=u'utf-8')

def javascript_path( js_name ):
	"""
	:return: A path to a javascript resource of this package, suitable for passing to phantomjs.
	:raises Exception: If the resource does not exist
	"""
	js_name = 'js/' + js_name
	if not resource_exists( __name__, js_name ):
		raise Exception( "Resource %s not found" % js_name )
	return resource_filename( __name__, js_name )
