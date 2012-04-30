#!/usr/bin/env python
"""
Utilities for working with :mod:`xml.dom.minidom` objects.
$Id$
"""
from __future__ import print_function, unicode_literals
import io

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
