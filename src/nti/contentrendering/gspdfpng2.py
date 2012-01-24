#!/usr/bin/env python
import os,tempfile, re, tempfile
from plasTeX.Logging import getLogger
import plasTeX.Imagers, glob, sys, os
from concurrent.futures import ProcessPoolExecutor
import resources
from collections import defaultdict

log = getLogger(__name__)
depthlog = getLogger('render.images.depth')
status = getLogger('status')
imagelog = getLogger('imager')

import plasTeX.Imagers
from plasTeX.Imagers import Image, WorkingFile
import subprocess
import math

status = getLogger('status')

gs = 'gs'
if sys.platform.startswith('win'):
	gs = 'gswin32c'

import plasTeX.Imagers.gspdfpng

## def _size(page,key):
## 	width_in_pt, height_in_pt = subprocess.Popen( "pdfinfo -box -f %d images.out | grep MediaBox | awk '{print $4,$5}'" % (page), shell=True, stdout=subprocess.PIPE).communicate()[0].split()
## 	return (key, width_in_pt, height_in_pt)

def _size(key, png):
	width_in_pt, height_in_pt = subprocess.Popen( "identify %s | awk '{print $3}'" % (png), shell=True, stdout=subprocess.PIPE).communicate()[0].split('x')
	return (key, width_in_pt, height_in_pt)

def _scale(input, output, scale, defaultScale):
	# Use IM to scale. Must be top-level to pickle
	#scale is 1x, 2x, 4x
	return os.system( 'convert %s -resize %d%% PNG32:%s' % (input, 100*(scale/defaultScale) , output) )

class GSPDFPNG2(plasTeX.Imagers.gspdfpng.GSPDFPNG):
	""" Imager that uses gs to convert pdf to png, using PDFCROP to handle the scaling """
	command = ('%s -dSAFER -dBATCH -dNOPAUSE -sDEVICE=pngalpha ' % gs) + \
			  '-dGraphicsAlphaBits=4 -sOutputFile=img%d.png'
	compiler = 'pdflatex'
	fileExtension = '.png'
	size=500
	scaleFactor = 1
	defaultScaleFactor = 4.0

	def executeConverter(self, output):
		open('images.out', 'wb').write(output.read())
		# Now crop
		# We complain about images being raised above the baseline, yet we have the margin set to 3?
		#os.system( "pdfcrop --hires --margin 3 images.out images.out" )
		os.system( "pdfcrop --hires images.out images.out" )

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

		options = ''
		if self._configOptions:
			for opt, value in self._configOptions:
				opt, value = str(opt), str(value)
				if ' ' in value:
					value = '"%s"' % value
				options += '%s %s ' % (opt, value)

		res = os.system('%s -r%d %s%s' % (self.command, self.size ,options, 'images.out')), None




		if self.scaleFactor != None:
			self.scaleImages()

		pngs=glob.glob('img*.png')
		pngs.sort(lambda a,b: cmp(int(re.search(r'(\d+)\.\w+$',a).group(1)),
									int(re.search(r'(\d+)\.\w+$',b).group(1))))

		# Record the fact that we've cropped them (in parallel, getting the size takes time)
		with ProcessPoolExecutor() as executor:
			for the_tuple in executor.map( _size, self.images.keys(), pngs ):
				img = self.images[the_tuple[0]]
				img._cropped = True
				img.width = math.ceil( float(the_tuple[1]) ) / 1.3
				img.height = math.ceil( float(the_tuple[2]) ) / 1.3
				#img.depth = -3

		return res

	def writePreamble( self, document ):
		""" Because we do our own cropping, we don't need the registration mark. Hence, we define that to do nothing; the
		superclass then does NOT define it. """
		self.source.write( "\\newcommand{\plasTeXregister}{}" )
		super(GSPDFPNG2,self).writePreamble( document )

	def scaleImages(self):
		" Uses ImageMagick to scale the images in parallel "
		with ProcessPoolExecutor() as executor:
			pngs=glob.glob('img*.png')
			for i in executor.map( _scale, pngs, pngs, [self.scaleFactor for x in pngs], [self.defaultScaleFactor for x in pngs]):
				pass


def _invert(input, output):
	return os.system('convert %s -negate %s' % (input, output))

Imager = GSPDFPNG2

copy=resources.copy


class ResourceGenerator(resources.ImagerResourceGenerator):

	scales = [1, 2, 4]
	shouldInvert = True

	def __init__(self, document):
		super(ResourceGenerator, self).__init__(document, Imager)

	def generateResources(self, sources, db):
		generatableSources = [s for s in sources if self.canGenerate(sources)]

		rsg = self.createResourceSetGenerator()
		rsg.imager.scaleFactor = None  #We scale them on our side

		for source in sources:
			#TODO newImage completely ignores the concept of imageoverrides
			rsg.addResource(source)

		processed = rsg.processSource()

		origSources, origImages = zip(*processed)

		#Create a tempdir to work in
		tempdir = tempfile.mkdtemp()

		imagesToResizeSource = []
		imagesToResizeDest = []

		allNewImages = []

		for source, image in processed:
			if image is None or image.width is None or image.height is None:
				raise Exception( "Unable to generate image for '%s' (%s)" % (source, image) )
			for scale in self.scales:
				print '%s %s %s %s' % (image.width, image.height, scale, rsg.imager.defaultScaleFactor)
			   	newImage = self.makeImage( os.path.join( tempdir,
														 self.__newNameFromOrig(image.path,
																				scale,
																				False)),
											image.width * (scale / rsg.imager.defaultScaleFactor),
											image.height * (scale/rsg.imager.defaultScaleFactor),
											image.depth )

				newImage._scaleFactor = scale
				newImage._source = source

				allNewImages.append(newImage)

				#Simple copy
				if newImage._scaleFactor == rsg.imager.defaultScaleFactor:
					copy(image.path, newImage.path)
				else:
					imagesToResizeSource.append(image)
					imagesToResizeDest.append(newImage)


		#Do the resize
		with ProcessPoolExecutor() as executor:
				for i in executor.map( _scale,
									   [image.path for image in imagesToResizeSource],
									   [image.path for image in imagesToResizeDest],
									   [image._scaleFactor for image in imagesToResizeDest],
									   [rsg.imager.defaultScaleFactor for x in imagesToResizeSource] ):
					pass

		for newImage in allNewImages:
			db.setResource(newImage._source, [self.resourceType, 'orig', newImage._scaleFactor], newImage)


		#Now invert
		if self.shouldInvert:
			allInvertedImages = []
			for scale in self.scales:
				for origImage in allNewImages:
					newImage = self.makeImage( os.path.join( tempdir,
															 self.__newNameFromOrig(origImage.path,
																					scale,
																					True)),
												origImage.width,
												origImage.height,
												origImage.depth )
					allInvertedImages.append(newImage)

			with ProcessPoolExecutor() as executor:
				for i in executor.map(_invert, [image.path for image in allNewImages], [image.path for image in allInvertedImages]):
					pass

			for origImage, newImage in zip(allNewImages, allInvertedImages):
				db.setResource(origImage._source, [self.resourceType, 'inverted', origImage._scaleFactor], newImage)


	def makeImage(self, path, width, height, depth, cropped=True):
		image = Image(os.path.basename(path), None)
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



	## def convert(self, output, resourcesets):
	## 	imager=self.imager

	## 	if not imager:
	## 		log.warning('No imager command is configured.  ' +
	## 					'No images will be created.')
	## 		return []x


	## 	cwd = os.getcwd()

	## 	# Make a temporary directory to work in
	## 	baseTemp = tempfile.mkdtemp()
	## 	os.chdir(baseTemp)

	## 	# Execute converter

	## 	scaledImages={1:None, 2:None, 4:None}

	## 	tmpLocations={}

	## 	for scale in scaledImages.keys():

	## 		subTempDir=tempfile.mkdtemp(dir=baseTemp)
	## 		tmpLocations[scale]=subTempDir
	## 		os.chdir(subTempDir)
	## 		output.seek(0)
	## 		scaledImages[scale]=self.__generateWithScaleFactor(output, resourcesets, scale)
	## 		os.chdir(baseTemp)

	## 	invertedImages={1:None, 2:None, 4:None}


	## 	for scale in scaledImages.keys():
	## 		os.chdir(tmpLocations[scale])

	## 		sources = scaledImages[scale]
	## 		dests=[]
	## 		for img in sources:
	## 			root, ext = os.path.splitext(img)
	## 			dests.append('%s_invert%s'%(root, ext))

	## 		with ProcessPoolExecutor() as executor:
	## 			for i in executor.map(_invert, sources, dests):
	## 				pass

	## 		invertedImages[scale]=dests
	## 		os.chdir(baseTemp)



	## 	if PILImage is None:
	## 		log.warning('PIL (Python Imaging Library) is not installed.	 ' +
	## 					'Images will not be cropped.')

	## 	#Create an inverted images to go with it




	## 	os.chdir(cwd)



	## 	# Move images to their final location and create img objects to return
	## 	for scale in scaledImages.keys():
	## 		tempdir=tmpLocations[scale]
	## 		for tmpPath, tmpPathInverted, resourceset in zip(scaledImages[scale], invertedImages[scale], resourcesets):

	## 			imageObj = self.__createImageObject(resourceset, tmpPath, '%sx'%scale)

	## 			imageObjInv = self.__createImageObject(resourceset, tmpPathInverted, '%sx'%scale)

	## 			if not self.resourceType in  resourceset.resources:
	## 				resourceset.resources[self.resourceType]={}

	## 			resourceset.resources[self.resourceType][scale]=(imageObj, imageObjInv)

	## 			self.__moveImage(os.path.join(tempdir, tmpPath), imageObj.path)
	## 			self.__moveImage(os.path.join(tempdir, tmpPathInverted), imageObjInv.path)



	## 	# Remove temporary directory
	## 	shutil.rmtree(baseTemp, True)

	## def __moveImage(self, source, dest):
	## 	#print 'Moving %s to %s' % (source, dest)
	## 	# Move the image
	## 	directory = os.path.dirname(dest)
	## 	if directory and not os.path.isdir(directory):
	## 		os.makedirs(dest)
	## 	try:
	## 		shutil.copy2(source, dest)
	## 	except OSError:
	## 		shutil.copy(source, dest)


	## def __generateWithScaleFactor(self,output, resourcesets, factor):
	## 	imager=self.imager
	## 	imager.scaleFactor=factor

	## 	rc, images = imager.executeConverter(output)
	## 	if rc:
	## 		log.warning('Image converter did not exit properly.	 ' +
	## 					'Images may be corrupted or missing.')
	## 	#print "Converted images are"
	## 	#print images

	## 	# Get a list of all of the image files
	## 	if images is None:
	## 		images = [f for f in os.listdir('.')
	## 						if re.match(r'^img\d+\.\w+$', f)]
	## 	if len(images) != len(resourcesets):
 	## 		log.warning('The number of images generated (%d) and the number of images requested (%d) is not the same.' % (len(images), len(nodes)))

	## 	# Sort by creation date
	## 	#images.sort(lambda a,b: cmp(os.stat(a)[9], os.stat(b)[9]))

	## 	images.sort(lambda a,b: cmp(int(re.search(r'(\d+)\.\w+$',a).group(1)),
	## 								int(re.search(r'(\d+)\.\w+$',b).group(1))))

	## 	return images



	## def __createImageObject(self, resourceset, orig, fname):
	## 	#Create a dest for the image
	## 	finalPath = os.path.join(resourceset.path, orig)


	## 	if os.path.exists(finalPath):
	## 		name, ext=os.path.splitext(orig)
	## 		finalPath=os.path.join(os.path.dirname(finalPath),('%s_%s%s'%(name, fname, ext)))

	## 	print 'Moving image for %s to %s' % (resourceset.source, finalPath)

	## 	imageObj = Image(finalPath, self.config['images'])

	## 			# Populate image attrs that will be bound later
	## 	if self.imageAttrs:
	## 		tmpl = string.Template(self.imageAttrs)
	## 		vars = {'filename':filename}
	## 		for name in ['height','width','depth']:
	## 			if getattr(img, name) is None:
	## 				vars['attr'] = name
	## 				value = DimensionPlaceholder(tmpl.substitute(vars))
	## 				value.imageUnits = self.imageUnits
	## 				setattr(img, name, value)

	## 	return imageObj
