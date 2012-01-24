#!/usr/bin/env PYTHONPATH=/Users/jmadden/Projects/AoPS/src/main/ /opt/local/bin/python2.7

import BaseHTTPServer
import urllib

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):

	def do_GET( self ):

		self.send_response( 200 )
		self.send_header( 'Content-Type',  'text/html' )
		self.end_headers()

		texsource = urllib.unquote( self.path.lstrip( '/' ) )
		if not texsource:
			texsource = '\\frac{d}{dx}\\sqrt{x} = \\frac{d}{dx}x^{\\frac{1}{2}} = \\frac{1}{2}x^{-\\frac{1}{2}} = \\frac{1}{2\\sqrt{x}}'

		html = """
	<html>
	<head>
		<link rel="stylesheet" type="text/css" href="http://laughinghan.github.com/mathquill/mathquill.css" />
	</head>
	<body>
		<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js" ></script>
		<script type="text/javascript" src="http://laughinghan.github.com/mathquill/mathquill.js" ></script>
		<span class="mathquill-embedded-latex">%s</span>
		</body>
		</html>""" % texsource

		print >> self.wfile, html




def main():
	httpd = BaseHTTPServer.HTTPServer( ('', 8080), Handler )
	httpd.serve_forever()

if __name__ == '__main__':
	main()
