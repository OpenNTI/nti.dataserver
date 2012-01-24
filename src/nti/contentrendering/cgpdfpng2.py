#!/usr/bin/env python2.7

"""
This program converts a multipage PDF document to a series of PNG images
using the OS X CoreGraphics library via the Quartz bridge from PyObjc.

"""

import sys, os
from optparse import OptionParser
import resources


from Quartz import *


__version__ = '0.1'

def _writeImgToFile( filename, img ):
	url = CFURLCreateWithFileSystemPath( None, filename, kCFURLPOSIXPathStyle, False )
	dst = CGImageDestinationCreateWithURL( url, 'public.png', 1, None )
	CGImageDestinationAddImage( dst, img, None )
	CGImageDestinationFinalize( dst )

def transform( options, inputfile ):

	result = []

	# FIXME: See below.
	print 'croping'
	os.system( "pdfcrop --hires --margin 3 %s images.out" % inputfile)
	# TODO: Temp names
	inputfile = 'images.out'

	pdf = CGPDFDocumentCreateWithProvider(
				CGDataProviderCreateWithFilename(inputfile))

	# Determine output filenames
	pdfPages = CGPDFDocumentGetNumberOfPages( pdf )
	output = options.output
	if output is None:
		ext = '.png'
		if pdfPages > 1:
			ext = '%d.png'
		output = os.path.splitext(inputfile)[0] + ext

	for pageNumber in xrange(1, pdfPages + 1):
		if pdfPages > 1:
			filename = output % pageNumber
		else:
			filename = output

		# Get content information
		page = CGPDFDocumentGetPage( pdf, pageNumber )
		#FIXME: This always returns the same size, the page size, no
		#matter which Box I request. Therefore, we must first run
		#PDFCROP to pre-crop the pages. Need access to the hires
		#bounding box, which is in the page dictionary, but the
		#dictionary functions don't work due to bridge issues
		box = CGPDFPageGetBoxRect( page, kCGPDFCropBox )
		origin = box.origin
		size = box.size

		newwidth = float(options.magnification) * size.width
		newheight = float(options.magnification) * size.height

		# Create new image from page
		ctx = CGBitmapContextCreate( None, int(newwidth), int(newheight), 8, int(newwidth) * 4, CGColorSpaceCreateDeviceRGB(), kCGImageAlphaPremultipliedLast )
		CGContextScaleCTM( ctx, options.magnification, options.magnification )

		CGContextSetInterpolationQuality( ctx, kCGInterpolationHigh )
		CGContextSetAllowsAntialiasing( ctx, True )
		CGContextSetShouldAntialias( ctx, True )
		#Not in bridge
		#CGContextSetAllowsFontSmoothing( ctx, True )
		CGContextSetShouldSmoothFonts( ctx, True )


		CGContextDrawPDFPage( ctx, page )

		img = CGBitmapContextCreateImage( ctx )

		if options.scaledown:
			w = int(newwidth / float(options.scaledown))
			h = int(newheight / float(options.scaledown))

			ctx = CGBitmapContextCreate( None, w, h, 8, w * 4, CGColorSpaceCreateDeviceRGB(), kCGImageAlphaPremultipliedLast )
			CGContextSetInterpolationQuality( ctx, kCGInterpolationHigh )
			CGContextSetAllowsAntialiasing( ctx, True )
			CGContextSetShouldAntialias( ctx, True )
			#Not in bridge
			#CGContextSetAllowsFontSmoothing( ctx, True )
			CGContextSetShouldSmoothFonts( ctx, True )
			# pageRect = CG.CGRectMake(0, 0, w, h)
			# c.drawImage(pageRect.inset(0, 0), img)
			CGContextDrawImage( ctx, CGRect( CGPoint(0, 0), CGSize(w, h) ), img )
			img = CGBitmapContextCreateImage( ctx )

		_writeImgToFile( filename, img )


		# # Write the file
		sys.stdout.write('[%s]' % filename)
		# c.writeToFile(filename, CG.kCGImageFormatPNG)
		result += filename

	return result


try:
	import plasTeX
	import plasTeX.Imagers
	import plasTeX.Imagers.gspdfpng
	class CGPDFPNG2(plasTeX.Imagers.gspdfpng.GSPDFPNG):
		""" Imager that uses OSX CG to convert pdf to png, using PDFCROP to handle the scaling """
		compiler = 'pdflatex'
		fileExtension = '.png'

		def executeConverter(self, output):
			open('images.out', 'wb').write(output.read())
			# Now crop it

			options = self
			# We have to produce an image of reasonable dimensions
			# since the pixel values wind up in the HTML. To get
			# smooth drawing, we draw big then scale down
			options.magnification = 6.0
			options.scaledown = 4.0
			options.output = 'img%d.png'

			files = transform( options, 'images.out' )

			return (0, None)

		#	def scaleImages(self):
		#		" Uses ImageMagick to scale the images in parallel "
		#		with ProcessPoolExecutor() as executor:
		#			for i in executor.map( _scale, glob.glob( 'img*.png') ):
		#				pass

	Imager = CGPDFPNG2
except ImportError:
	pass




def main(args):
	parser = OptionParser(usage='usage: %prog [ options ] filename.pdf',
					  version='%%prog %s' % __version__)
	parser.add_option('-o', '--output', action='store', default=None,
				  type='string', dest='output', metavar='FILENAME',
				  help='output filename template')
	parser.add_option('-m', '--magnification', action='store', default=1.0,
				  type='float', dest='magnification', metavar='NUM',
				  help='magnification level applied to input document')
	parser.add_option('-s', '--scaledown', action='store', default=1.0,
				  type='float', dest='scaledown', metavar='NUM',
				  help='scale factor to reduce size of output images')
	(options, args) = parser.parse_args()

	if len(args) > 1:
		parser.error('Too many arguments')
		if len(args) < 1:
			parser.error('A filename argument is required')

	inputfile = args[0]
	if not os.path.isfile(inputfile):
		parser.error('%s is not a valid file' % inputfile)

	print 'cgpdfpng %s' % __version__

	transform( options, inputfile )

if __name__ == '__main__':
	main( sys.argv )
