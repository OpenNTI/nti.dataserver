#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

import os

from nti.contentrendering import ConcurrentExecutor
from nti.contentrendering import javascript_path, run_phantom_on_page
from nti.contentrendering import interfaces

_rasterize_script = javascript_path( 'rasterize.js')
thumbnailsLocationName = 'thumbnails'

def _generateImage(page_location, page_ntiid, output_file_path):
	"""
	Given an absolute path pointing to an HTML file, produce a PNG
	thumbnail image for the page in ``output_file_path``.

	This function may raise :class:`subprocess.CalledProcessError`,
	:class:`ValueError` or :class:`TypeError`.

	:return: A two-tuple, the page's NTIID from ``page_ntiid`` and the path to the generated
		thumbnail.
	"""
	# Rasterize the page to an image file as a side effect
	# For BWC, the size is odd, at best:
	# Generate a 180 x 251 image, at 25% scale
	run_phantom_on_page( page_location, _rasterize_script,
						 args=(output_file_path, "180", "251", "0.25"),
						 expect_no_output=True )

	return (page_ntiid, output_file_path)


def transform(book, context=None):
	"""
	Generate thumbnails for all pages and stuff them in the toc.
	"""

	eclipseTOC = book.toc

	# generate a place to put the thumbnails
	thumbnails_dir = os.path.join(book.contentLocation, thumbnailsLocationName)

	if not os.path.isdir(thumbnails_dir):
		os.mkdir(thumbnails_dir)

	# Create the parallel sets of arguments
	# for _generateImage
	page_paths = []
	page_ntiids = []
	thumbnail_paths = []

	for page in book.pages.values():
		page_paths.append( os.path.join( book.contentLocation, page.location ) )
		page_ntiids.append( page.ntiid )
		thumbnail_name = '%s.png' % os.path.splitext(page.filename)[0]
		thumbnail_paths.append( os.path.join( thumbnails_dir, thumbnail_name ) )

	with ConcurrentExecutor() as executor:
		# If _generateImage raises an exception, we will fail to
		# unpack the tuple result (because the exception is returned)
		# and this function will fail

		for ntiid, thumbnail_file in executor.map( _generateImage,
												   page_paths, page_ntiids, thumbnail_paths ):

			eclipseTOC.getPageNodeWithNTIID(ntiid).attributes['thumbnail'] = os.path.relpath(thumbnail_file, start=book.contentLocation)
	eclipseTOC.save()

component.moduleProvides(interfaces.IRenderedBookTransformer)
