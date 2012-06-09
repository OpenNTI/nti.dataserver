#!/usr/bin/env python

import os
import plasTeX.Imagers
from concurrent.futures import  ProcessPoolExecutor
import subprocess
import math

from nti.contentrendering import resources
from . import converters, interfaces

def do_convert(  page ):
	# convert to svg
	# must be toplevel function so it can be pickled
	filename = 'img%d.svg' % page
	subprocess.check_call( ('pdf2svg', 'images.pdf', filename, str(page) ) )

	if not open(filename).read().strip():
		os.remove(filename)
		print 'Failed to convert %s' % filename
		return None

	#Then remove the width and height boxes since this interacts badly with
	#HTML embedding
	os.system( "sed -i '' 's/width=.*pt\"//' %s" % filename )

	# Get the width and height from the media box since we're not cropping it
	# in Python code
	width_in_pt, height_in_pt = subprocess.Popen( "pdfinfo -box -f %d images.pdf | grep MediaBox | awk '{print $4,$5}'" % (page), shell=True, stdout=subprocess.PIPE).communicate()[0].split()
	return (filename, width_in_pt, height_in_pt)


class PDF2SVG(plasTeX.Imagers.VectorImager):
	""" Imager that uses pdf2svg """
	fileExtension = '.svg'
	verification = 'pdf2svg --help'
	compiler = 'pdflatex'

	def executeConverter(self, output):
		open('images.pdf', 'w').write(output.read())
		#Crop all the pages of the PDF to the exact size
		os.system( "pdfcrop --hires --margin 0 images.pdf images.pdf" )
		# We must mark these as cropped
		for img in self.images.values():
			img._cropped = True

		#Find out how many pages to expect

		maxpages = int(subprocess.Popen( "pdfinfo images.pdf | grep Pages | awk '{print $2}'", shell=True, stdout=subprocess.PIPE).communicate()[0])

		filenames = []
		with ProcessPoolExecutor( max_workers=16 ) as executor:
			for the_tuple in zip(executor.map( do_convert, xrange( 1, maxpages + 1 ) ),self.images.values()):
				filenames.append( the_tuple[0][0] )

				the_tuple[1].width = math.ceil( float(the_tuple[0][1]) ) * 1.3
				the_tuple[1].height = math.ceil( float(the_tuple[0][2]) ) * 1.3
				# FIXME: The depth (height above baseline) is not correct
				the_tuple[1].depth = -3

		return 0, filenames

	def verify(self):
		return True

Imager = PDF2SVG

class ResourceGenerator(converters.ImagerContentUnitRepresentationBatchConverter):
	def __init__(self, document):
		super(ResourceGenerator, self).__init__(document, Imager)
