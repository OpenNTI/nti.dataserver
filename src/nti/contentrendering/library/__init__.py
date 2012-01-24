#!/usr/bin/env python2.7

import sys
import plistlib

def main( args ):

	online = { 'icon': '/prealgebra/icons/chapters/PreAlgebra-cov.png',
			   'href': '/prealgebra/index.html',
			   'root': '/prealgebra/',
			   'index': '/prealgebra/eclipse-toc.xml',
			   'title': 'Prealgebra',
			   'installable': True,
			   'version': '1.0',
			   'archive': '/prealgebra/archive.zip' }

	other = { 'icon': '/prealgebra/icons/chapters/Cat.tif',
			   'href': '/prealgebra/DNE.html',
			   #'index': '/prealgebra/eclipse-toc.xml',
			  'root': '/prealgebra/',
			   'title': 'Introduction to Catculus',
			   'installable': True,
			   'version': '1.0',
			   'archive': '/prealgebra/archive.zip' }

	root = { 'icon': '/prealgebra/icons/chapters/Chalkboard.tif',
			 'title': 'Library',
			 'titles': [online,other] }


	dest = sys.stdout
	if args:
		dest = args[0]
	plistlib.writePlist( root, dest )


if __name__ == '__main__':
	main( sys.argv[1:] )
