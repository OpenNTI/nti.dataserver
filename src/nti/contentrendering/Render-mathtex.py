#!/usr/bin/env PYTHONPATH=/Users/jmadden/Projects/AoPS/src/main/ /opt/local/bin/python2.7

import BaseHTTPServer
import urllib

from mathtex.mathtex_main import Mathtex
from mathtex.fonts import UnicodeFonts

the_unicode = UnicodeFonts( rm='Symbola', default='Symbola' )

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

	def do_GET( self ):
		print self.path

		self.send_response( 200 )
		self.send_header( 'Content-Type',  'image/svg+xml' )
		self.end_headers()

		texsource = '$' + urllib.unquote( self.path.lstrip( '/' ) ) + '$'
		print texsource
		m = Mathtex( texsource, the_unicode )
		# The SVG backend uses PyCairo's SVGSurface, which accepts any
		# file-like object, not just a filename string, to write to
		m.save( self.wfile, 'svg' )



def main():
	httpd = BaseHTTPServer.HTTPServer( ('', 8080), Handler )
	httpd.serve_forever()

if __name__ == '__main__':
	main()
