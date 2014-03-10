#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A resource converter to create SVG.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import math
import subprocess

import plasTeX.Imagers

from . import converters
from .. import ConcurrentExecutor as ProcessPoolExecutor

from PyPDF2 import PdfFileReader

def _do_convert(page, input_filename='images.pdf'):
	"""
	Convert a page of a PDF into SVG using ``pdf2svg`` (which must be
	accessible on the system PATH).

	FIXME: We assume the existence of ``images.pdf`` in the current directory.

	:param int page: The page of the document to convert, in the current directory.
	:return: A tuple giving the relative path of the SVG filename, plus the width and
		height in points, or None of the conversion failed.
	"""
	# convert to svg
	# must be toplevel function so it can be pickled
	filename = 'img%d.svg' % page
	# TODO: in other converters we've observed hangs if exceptions are raised
	# in the process pool. Happen here?
	subprocess.check_call( ('pdf2svg', input_filename, filename, str(page) ) )

	with open(filename, 'rb') as f:
		if not f.read().strip():
			os.remove(filename)
			logger.warn( 'Failed to convert %s', filename )
			return None

	#Then remove the width and height boxes since this interacts badly with
	#HTML embedding
	exitcode = os.system( "sed -i -e 's/width=.*pt\"//' %s" % filename )
	if exitcode:
		logger.warn('Failed to convert %s', filename)
		return None

	# Get the width and height from the media box since we're not cropping it
	# in Python code
	with open(input_filename, 'rb') as f:
		mediaBox = PdfFileReader(f).getPage(page).mediaBox
		width_in_pt, height_in_pt = mediaBox.getWidth(), mediaBox.getHeight()

	return (filename, width_in_pt, height_in_pt)

class PDF2SVG(plasTeX.Imagers.VectorImager):
	"""
	Imager that uses pdf2svg.

	Internally executes concurrently.

	"""
	fileExtension = '.svg'
	verification = 'pdf2svg --help'
	compiler = 'pdflatex'

	def executeConverter(self, output):
		open('images.pdf', 'w').write(output.read())
		# Crop all the pages of the PDF to the exact size
		# os.system( "pdfcrop --hires --margin 0 images.pdf images.pdf" )
		with open('/dev/null', 'w') as dev_null:
			subprocess.check_call(
					 ('pdfcrop', '--hires', '--margin', '0', 'images.pdf', 'images.pdf'),
					  stdout=dev_null, stderr=dev_null)
		# We must mark these as cropped
		for img in self.images.values():
			img._cropped = True

		# Find out how many pages to expect
		# TODO: Use of shell is deprecated.
		cmd = "pdfinfo images.pdf | grep Pages | awk '{print $2}'"
		result = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).communicate()
		logger.info("pdf info max pages output %s", result)
		maxpages = int(result[0].strip())

		filenames = []
		with ProcessPoolExecutor(max_workers=16) as executor:
			_images = self.images.values()
			for the_tuple in zip(executor.map(_do_convert, xrange(1, maxpages + 1)), _images):
				filenames.append(the_tuple[0][0])

				the_tuple[1].width = math.ceil(float(the_tuple[0][1])) * 1.3
				the_tuple[1].height = math.ceil(float(the_tuple[0][2])) * 1.3
				# FIXME: The depth (height above baseline) is not correct
				the_tuple[1].depth = -3

		return 0, filenames

	def verify(self):
		return True

Imager = PDF2SVG # An alias for use as a plastex imager module

class PDF2SVGBatchConverter(converters.ImagerContentUnitRepresentationBatchConverter):

	def __init__(self, document):
		super(PDF2SVGBatchConverter, self).__init__(document, PDF2SVG)
