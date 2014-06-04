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
import platform
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

	:param int page: The page of the document to convert, in the current directory. 1-based, not 0-based.
	:return: A string giving the relative path of the SVG filename,  or None of the conversion failed.
	"""
	# convert to svg
	# must be toplevel function so it can be pickled
	filename = 'img%d.svg' % page
	# TODO: in other converters we've observed hangs if exceptions are raised
	# in the process pool. Happen here?
	__traceback_info__ = ('pdf2svg', filename)
	subprocess.check_call( ('pdf2svg', input_filename, filename, str(page) ) )

	with open(filename, 'rb') as f:
		if not f.read().strip():
			os.remove(filename)
			logger.warn( 'Failed to convert %s', filename )
			return None

	# Then remove the width and height boxes since this interacts badly with
	# HTML embedding.
	# NOTE: The behaviour of -i is different between GNU sed and BSD sed;
	# On OS X we assume BSD sed, otherwise we assume GNU sed
	pattern = 's/width=.*pt\"//'

	if platform.system() == 'Darwin':
		sed_args = ('sed', '-i', '', '-e', pattern, filename)
	else:
		sed_args = ('sed', '-i', '-e', pattern, filename)
	subprocess.check_call(sed_args)

	return filename

class PDF2SVG(plasTeX.Imagers.VectorImager):
	"""
	Imager that uses pdf2svg.

	Internally executes concurrently.

	"""
	fileExtension = '.svg'
	verification = 'pdf2svg --help'
	compiler = 'pdflatex'

	def executeConverter(self, output):
		with open('images.pdf', 'wb') as f:
			f.write(output.read())
		# Crop all the pages of the PDF to the exact size
		# os.system( "pdfcrop --hires --margin 0 images.pdf images.pdf" )
		with open('/dev/null', 'w') as dev_null:
			cmd = ('pdfcrop', '--hires', '--margin', '0', 'images.pdf', 'images.pdf')
			__traceback_info__ = cmd
			subprocess.check_call(
				cmd,
				stdout=dev_null, stderr=dev_null)
		_images = list(self.images.values())

		# Find out how many pages to expect and record file sizes
		with open('images.pdf', 'rb') as f:
			pdf = PdfFileReader(f)
			maxpages = pdf.getNumPages()

			for i in range(maxpages):
				mediaBox = pdf.getPage(i).mediaBox
				width_in_pt, height_in_pt = mediaBox.getWidth(), mediaBox.getHeight()

				# We must mark these as cropped and give them a size
				# Note that self.images is an ordereddict, so they match up by index
				image = _images[i]
				image._cropped = True
				image.width = math.ceil(width_in_pt) * 1.8
				image.height = math.ceil(height_in_pt) * 1.8
				# FIXME: The depth (height above baseline) is not correct
				image.depth = -3

		filenames = []
		with ProcessPoolExecutor(max_workers=16) as executor:
			for filename in executor.map(_do_convert, xrange(1, maxpages + 1)):
				filenames.append(filename)

		return 0, filenames

	def verify(self):
		return True

Imager = PDF2SVG # An alias for use as a plastex imager module

class PDF2SVGBatchConverter(converters.ImagerContentUnitRepresentationBatchConverter):

	def __init__(self, document):
		super(PDF2SVGBatchConverter, self).__init__(document, PDF2SVG)
