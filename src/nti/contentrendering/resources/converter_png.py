#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A resource converter to create PNGs.

..note:: This module is currently not tested.

$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

import os
import tempfile
import re
import shutil
import stat
import glob
import time

from nti.contentrendering import ConcurrentExecutor as ProcessPoolExecutor
from nti.contentrendering.resources import converters, interfaces
from zope import interface


import plasTeX.Imagers
from plasTeX.Imagers import Dimension, Image
import subprocess
import math

gs = 'gs'

import plasTeX.Imagers.gspdfpng

## def _size(page,key):
## 	width_in_pt, height_in_pt = subprocess.Popen( "pdfinfo -box -f %d images.out | grep MediaBox | awk '{print $4,$5}'" % (page), shell=True, stdout=subprocess.PIPE).communicate()[0].split()
## 	return (key, width_in_pt, height_in_pt)

def _size(key, png):
	# identify, from ImageMagick, is much easier to work with than pdfinfo --box
	width_in_pt, height_in_pt = subprocess.Popen( "identify %s | awk '{print $3}'" % (png), shell=True, stdout=subprocess.PIPE).communicate()[0].split('x')
	return (key, width_in_pt, height_in_pt)

def _scale(input, output, scale, defaultScale):
	"""Scales the input file to the desired size and then sanitizes the result with pngcrush."""

	# Use IM to scale. Must be top-level to pickle
	# Scale is the fraction of defaultScale that we wise to scale the image to.  For example, if scale is 2 and
	# defaultScale is 1, then the image would be scaled to 1/2 the original size.
	command = [ 'convert', input, '-resize', '%f%%' % (100 * ( defaultScale / scale ) ), '%s' % output ]
	__traceback_info__ = command
	retval1 = subprocess.call( command )

	# Check that the out put file is not 0 bytes, if it is try, try again because something odd happened.
	while os.stat(output).st_size == 0:
		logger.warning('%s is empty!!!! Input was %s with size %s. Output scale was %s. Attempting to convert again.' % (output, input, os.stat(input).st_size, unicode(100 * ( defaultScale / scale ))))
		retval1 = subprocess.call( command )

	# SAJ: Only run PNG crush on non-zero length PNG files
	retval2 = 0
	if os.stat(output).st_size != 0:
		if '.png' in output:
			# Use pngcrush to clean the resized PNG.
			retval2 = _sanitize_png( output )
	else:
		logger.warning('Produced zero length file: %s' % output)

	# Make sure that the out put files are readable by all
	os.chmod(output, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

	return retval1 if (retval1 < retval2) else retval2

def _sanitize_png( image_file ):
	"""Uses the external pngcrush program to sanitize PNGs."""

	prefix = hex(int(time.time()*1000))
	tmp_file = tempfile.mkstemp(suffix='.png', prefix=prefix)[1]
	command = [ 'pngcrush', '-q', image_file, tmp_file ]
	__traceback_info__ = command

	retval = subprocess.call( command )

	if os.path.exists(tmp_file) and os.stat(tmp_file).st_size != 0:
		shutil.move( tmp_file, image_file )
	elif os.path.exists(tmp_file) and os.stat(tmp_file).st_size == 0:
		# SAJ: The second statement in this elif clause is not required, but it does make the
		# inteded logic clear.
		logger.warning('A zero-length file was created during sanitization. Passing on the unsanitized file.')
		os.remove(tmp_file)

	return retval


class _GSPDFPNG2(plasTeX.Imagers.gspdfpng.GSPDFPNG):
	"""
	Imager that uses gs to convert pdf to png, using PDFCROP to handle the scaling.

	Customized to work only with our :class:`GSPDFPNG2BatchConverter` class, so
	some features are removed.

	"""
	#command = ('%s -q -dSAFER -dBATCH -dNOPAUSE -sDEVICE=pngalpha ' % gs) + \
	#    '-dGraphicsAlphaBits=4 -sOutputFile=img%d.png'
	command = [ gs, '-q', '-dSAFER', '-dBATCH', '-dNOPAUSE', '-sDEVICE=pngalpha', '-dGraphicsAlphaBits=4',
		    '-sOutputFile=img%d.png']
	compiler = 'pdflatex'
	fileExtension = '.png'
	# SAJ: The relationship between resolution and defaultScaleFator is important to prevent the distortion of
	# the input images. When rasterizing vector graphics, oversampling improves the visual quality of the output.
	resolution = 144 # SAJ: Integer multiples of 72 work best.
	defaultScaleFactor = 1.0
	scaleFactor = 1

	def executeConverter(self, output):
		# Must have been called from the converter
		assert self.scaleFactor is None, "Scaling not supported"

		open('images.out', 'wb').write(output.read())
		# Now crop
		# We complain about images being raised above the baseline, yet we have the margin set to 3?
		#os.system( "pdfcrop --hires --margin 3 images.out images.out" )
		#os.system( "pdfcrop --hires images.out images.out" )
		# pdfcrop produces useless stdout data
		with open('/dev/null', 'w') as dev_null:
			command = ('pdfcrop', '--hires', 'images.out', 'images.out' )
			__traceback_info__ = command
			subprocess.call( command, stdout=dev_null, stderr=dev_null )

		#maxpages = int(subprocess.Popen( "pdfinfo images.out | grep Pages | awk '{print $2}'", shell=True, stdout=subprocess.PIPE).communicate()[0])
		# Record the fact that we've cropped them (in parallel, getting the size takes time)
		## with ProcessPoolExecutor() as executor:
		## 	for the_tuple in executor.map( _size, xrange(1, maxpages + 1 ), self.images.keys() ):
		## 		img = self.images[the_tuple[0]]
		## 		img._cropped = True
		## 		img.width = math.ceil( float(the_tuple[1]) ) * 1.3
		## 		img.height = math.ceil( float(the_tuple[2]) ) * 1.3
		## 		img.depth = -3
		## 	# TODO: This is in points, we want it in pixels; these are
		## 	# coming in too small
		## 	# We're arbitrarily assigning a height above baseline to match the margin

		#options = ''
		options = []
		if self._configOptions:
			for opt, value in self._configOptions:
				opt, value = str(opt), str(value)
				if ' ' in value:
					value = '"%s"' % value
				#options += '%s %s ' % (opt, value)
				options.extend( [ opt, value ] )

		self.command.append( '-r%d' % self.resolution)
		self.command.extend( options )
		self.command.append( 'images.out' )
		__traceback_info__ = self.command
		# SAJ: Turn the result of the subprocess call into a tuple.  This seems rather hackish.
		res = subprocess.call( self.command ), None

		pngs = glob.glob('img*.png')
		pngs.sort(lambda a,b: cmp(int(re.search(r'(\d+)\.\w+$',a).group(1)),
									int(re.search(r'(\d+)\.\w+$',b).group(1))))

		# Record the fact that we've cropped them (in parallel, getting the size takes time)
		with ProcessPoolExecutor() as executor:
			for the_tuple in executor.map( _size, self.images.keys(), pngs ):
				img = self.images[the_tuple[0]]
				img._cropped = True
				#img.width = math.ceil( float(the_tuple[1]) / 1.3 )
				#img.height = math.ceil( float(the_tuple[2]) / 1.3 )
				img.width = the_tuple[1]
				img.height = the_tuple[2]
				#img.depth = -3

		return res

	def writePreamble( self, document ):
		""" Because we do our own cropping, we don't need the registration mark. Hence, we define that to do nothing; the
		superclass then does NOT define it. """
		self.source.write( "\\newcommand{\plasTeXregister}{}" )
		super(_GSPDFPNG2,self).writePreamble( document )
		self.source.write('\\usepackage[b0paper]{geometry}\n')
		self.source.write('\\setlength{\\pdfpagewidth}{100.0cm}\n\\setlength{\\pdfpageheight}{141.4cm}\n')

	def scaleImages(self): # pragma: no cover
		raise NotImplementedError("Scaling is done in the converter.")

	def getImage(self, node):
		"""
		Get an image from the given node whatever way possible

		This method attempts to find an existing image using the
		`imageoverride' attribute.  If it finds it, the image is
		copied to the images directory.  If no image is available, 
		or there was a problem in getting the image, an image is 
		generated.

		Arguments:
		node -- the node to create the image from

		Returns:
		Image instance

		"""
		allowedTypes = [ '.png', '.jpeg', '.jpg', '.gif' ]

		name = getattr(node, 'imageoverride', None)
		if name is None:
			return self.newImage(node.source)

		if name in self.staticimages:
			return self.staticimages[name]

		# Copy or convert the image as needed
		path = self.newFilename()
		newext = os.path.splitext(path)[-1]
		oldext = os.path.splitext(name)[-1]
		try:
			directory = os.path.dirname(path)
			if directory and not os.path.isdir(directory):
				os.makedirs(directory)

			# Just copy the image for now, any necessary conversions will be handled later.
			if oldext.lower() in allowedTypes:
				path = os.path.splitext(path)[0] + os.path.splitext(name)[-1]
				shutil.copyfile(name, path)
				_t, width, height = _size( path, path )
				width = Dimension(width)
				height = Dimension(height)
				height.imageUnits = width.imageUnits = self.imageUnits

				img = Image(path, self.ownerDocument.config['images'], width=width, height=height)
				self.staticimages[name] = img
				return img

		# If anything fails, just let the imager handle it...
		except Exception, msg:
			logger.warning('%s in image "%s".	 Reverting to LaTeX to generate the image.' % (msg, name))
		return self.newImage(node.source)

def _invert(ifile, ofile):
	#return os.system('convert %s -negate %s' % (ifile, ofile))
	return subprocess.call( ['convert', ifile, '-negate', ofile ] )

from ._util import copy


class GSPDFPNG2BatchConverter(converters.ImagerContentUnitRepresentationBatchConverter):

	scales = (1,2,4)
	shouldInvert = False
	batch = 0

	def __init__(self, document):
		super(GSPDFPNG2BatchConverter, self).__init__(document, _GSPDFPNG2)

	def process_batch(self, content_units):

		rsg = self._new_batch_converter_driver()
		rsg.imager.scaleFactor = None  #We scale them on our side

		start = time.time()
		processed = rsg.convert_batch( content_units )
		end = time.time()
		if len(processed) != len(content_units):
			raise OSError( 'Expected %s files but only generated %s for batch %s' %
						   (len(content_units), len(processed), self.batch ) )
		elapsed = end - start
		logger.info( "%s resources generated in %ss for batch %s", len(processed), elapsed, self.batch )
		#origSources, origImages = zip(*processed)
		#origImages = processed

		#Create a tempdir to work in
		tempdir = tempfile.mkdtemp()

		imagesToResizeSource = []
		imagesToResizeDest = []

		allNewImages = []

		for image in processed:
			source = image.source
			if image is None or image.width is None or image.height is None:
				raise Exception( "Unable to generate image for '%s' (%s)" % (source, image) )
			for scale in self.scales:
			   	newImage = self.makeImage( os.path.join( tempdir,
									 self.__newNameFromOrig(image.path,
												scale,
												False)),
							   math.ceil(int(image.width) * (rsg.imager.defaultScaleFactor/scale)),
							   math.ceil(int(image.height) * (rsg.imager.defaultScaleFactor/scale)),
							   image.depth )

				newImage._scaleFactor = scale
				newImage._source = source
				newImage.source = source
				newImage.qualifiers = ('orig', scale) # TODO: We should define a named tuple class for our qualifiers
				interface.alsoProvides( newImage, interfaces.IContentUnitRepresentation )
				allNewImages.append(newImage)

				#Simple copy
				if newImage._scaleFactor == rsg.imager.defaultScaleFactor:
					copy(image.path, newImage.path)
				else:
					imagesToResizeSource.append(image)
					imagesToResizeDest.append(newImage)


		#Do the resize
		with ProcessPoolExecutor() as executor:
			for _ in executor.map( _scale,
								   [image.path for image in imagesToResizeSource],
								   [image.path for image in imagesToResizeDest],
								   [image._scaleFactor for image in imagesToResizeDest],
								   [rsg.imager.defaultScaleFactor for _ in imagesToResizeSource] ):
				pass



		#Now invert
		allInvertedImages = []
		if self.shouldInvert:
			for scale in self.scales:
				for origImage in allNewImages:
					newImage = self.makeImage( os.path.join( tempdir,
										 self.__newNameFromOrig(origImage.path,
													scale,
													True)),
								   origImage.width,
								   origImage.height,
								   origImage.depth )
					newImage.source = origImage.source
					newImage.qualifiers = ('inverted', scale)
					interface.alsoProvides( newImage, interfaces.IContentUnitRepresentation )
					allInvertedImages.append(newImage)

			with ProcessPoolExecutor() as executor:
				for _ in executor.map(_invert, [image.path for image in allNewImages], [image.path for image in allInvertedImages]):
					pass


		return allNewImages + allInvertedImages


	def makeImage(self, path, width, height, depth, cropped=True):
		image = Image(os.path.basename(path), None)
		# TODO: This is something of an abuse of things. We use this as a
		# Resource object even though it isn't really.
		image.path = path
		image.width = width
		image.height = height
		image.depth = depth
		image._cropped = cropped
		return image

	def __newNameFromOrig(self, name, size, inverted):
		dir, base = os.path.split(name)
		fname, ext = os.path.splitext(base)

		newName = '%s_%dx' % (fname, size)

		if inverted:
			newName += '_inverted'

		newName += '%s' % ext

		return newName
