#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import os
import sys
import time
import logging
import argparse
import functools
import subprocess

import zope.exceptions.log

from zope import component

import zope.dublincore.xmlmetadata

from plasTeX.Logging import getLogger
logger = getLogger(__name__)

from nti.contentrendering import archive
from nti.contentrendering import jsonpbuilder
from nti.contentrendering import contentchecks
from nti.contentrendering import tociconsetter
from nti.contentrendering import html5cachefile
from nti.contentrendering import ntiidlinksetter
from nti.contentrendering import contentsizesetter
from nti.contentrendering import relatedlinksetter
from nti.contentrendering import sectionvideoadder

from nti.contentrendering.render_document import parse_tex
from nti.contentrendering.render_document import resource_filename

from nti.contentrendering.interfaces import IRenderedBookIndexer
from nti.contentrendering.interfaces import IRenderedBookTransformer

from nti.contentrendering.RenderedBook import RenderedBook
from nti.contentrendering.resources.ResourceDB import ResourceDB
from nti.contentrendering.resources.ResourceRenderer import createResourceRenderer
from nti.contentrendering.resources.resourcetypeoverrides import ResourceTypeOverrides

DEFAULT_LOG_FORMAT = '[%(asctime)-15s] [%(name)s] %(levelname)s: %(message)s'

def _configure_logging(level='INFO', fmt=DEFAULT_LOG_FORMAT):
	numeric_level = getattr(logging, level.upper(), None)
	numeric_level = logging.INFO if not isinstance(numeric_level, int) else numeric_level
	logging.basicConfig(level=numeric_level)
	logging.root.handlers[0].setFormatter(zope.exceptions.log.Formatter(fmt))

def _catching(f):
	@functools.wraps(f)
	def y():
		try:
			f()
		except subprocess.CalledProcessError as spe:
			logger.exception("Failed to run subprocess")
			sys.exit(spe.returncode)
		except:
			logger.exception("Failed to run main")
			sys.exit(1)
	return y

def _set_argparser():
	arg_parser = argparse.ArgumentParser( description="Render NextThought content." )

	arg_parser.add_argument( 'contentpath',
							help="Path to top level content file." )
	arg_parser.add_argument( '-c', '--config',
							help='Used by render_content wrapper. Ignore if running '
								 'nti_render standalone.')
	arg_parser.add_argument( '--nochecking',
							 action='store_true',
							 default=False,
							 help="Perform content checks." )
	arg_parser.add_argument( '--noindexing',
							 action='store_true',
							 default=False,
							 help="Index content files." )
	arg_parser.add_argument('-o', '--outputformat',
							 default='xhtml',
							 help="Output format for rendered files. Default is xhtml" )
	arg_parser.add_argument( '--loglevel',
							 default='INFO',
							 help="Set logging level to INFO, DEBUG, WARNING, ERROR or "
							 	  "CRITICAL. Default is INFO." )
	return arg_parser


@_catching
def main():
	""" 
	Main program routine 
	"""
	argv = sys.argv[1:]
	arg_parser = _set_argparser()
	args = arg_parser.parse_args(args=argv)

	sourceFile = args.contentpath
	_configure_logging(args.loglevel)
	dochecking = not args.nochecking
	doindexing = not args.noindexing
	outFormat = args.outputformat

	logger.info("Start rendering for %s", sourceFile)
	start_t = time.time()
	document, components, jobname = parse_tex(sourceFile, outFormat=outFormat)
	
	db = None
	if outFormat in ('images', 'xhtml', 'text'):
		logger.info("Generating images")
		db = generateImages(document)

	if outFormat == 'xhtml':
		logger.info("Begin render")
		render(document, document.config['general']['renderer'], db)
		logger.info("Begin post render")
		postRender(document,
				   jobname=jobname,
				   context=components,
				   dochecking=dochecking,
				   doindexing=doindexing)
	elif outFormat == 'xml':
		logger.info("To Xml.")
		toXml(document, jobname)

	elif outFormat == 'text':
		logger.info("Begin render")
		render(document, document.config['general']['renderer'], db)

	logger.info("Write metadata.")
	write_dc_metadata(document, jobname)

	elapsed = time.time() - start_t
	logger.info("Rendering took %s(s)", elapsed)

def postRender(document,
			   contentLocation='.',
			   jobname='prealgebra',
			   context=None,
			   dochecking=True,
			   doindexing=True):
	# FIXME: This was not particularly well thought out. We're using components,
	# but named utilities, not generalized adapters or subscribers.
	# That makes this not as extensible as it should be.

	# We very likely will get a book that has no pages
	# because NTIIDs are not added yet.
	start_t = time.time()
	logger.info('Creating rendered book')
	book = RenderedBook(document, contentLocation)
	elapsed = time.time() - start_t
	logger.info("Rendered book created in %s(s)", elapsed)

	# This step adds NTIIDs to the TOC in addition to modifying
	# on-disk content.
	logger.info('Adding icons to toc and pages')
	tociconsetter.transform(book, context=context)

	logger.info('Storing content height in pages')
	contentsizesetter.transform(book, context=context)

	logger.info('Adding related links to toc')
	relatedlinksetter.performTransforms(book, context=context)

	# SAJ: Disabled until we determine what thumbnails we need and how to create them 
	# in a useful manner.
	# logger.info('Generating thumbnails for pages')
	# contentthumbnails.transform(book, context=context)

	# PhantomJS doesn't cope well with the iframes
	# for embedded videos: you get a black box, and we put them at the top
	# of the pages, so many thumbnails end up looking the same, and looking
	# bad. So do this after taking thumbnails.
	logger.info('Adding videos')
	sectionvideoadder.performTransforms(book, context=context)

	if dochecking:
		logger.info('Running checks on content')
		contentchecks.performChecks(book, context=context)

	contentPath = os.path.realpath(contentLocation)

	# TODO: Aren't the things in the archive mirror file the same things
	# we want to list in the manifest? If so, we should be able to combine
	# these steps (if nothing else, just list the contents of the archive to get the
	# manifest)
	logger.info("Creating html cache-manifest")
	html5cachefile.main(contentPath, contentPath)

	logger.info('Changing intra-content links')
	ntiidlinksetter.transform(book)

	# In case order matters, we sort by the name of the
	# utility. To register, use patterns like 001, 002, etc.
	# Ideally order shouldn't matter, and if it does it should be
	# handled by a specialized dispatching utility.
	for name, extractor in sorted(component.getUtilitiesFor(IRenderedBookTransformer)):
		if not IRenderedBookIndexer.providedBy(extractor):
			logger.info("Extracting %s/%s", name, extractor)
			extractor.transform(book)

	if doindexing and  not os.path.exists(os.path.join(contentPath, 'indexdir')):
		# We'd like to be able to run this with pypy (it's /much/ faster)
		# but some of the Zope libs we import during contentsearch (notably Persistent)
		# are not quite compatible. A previous version of this code made the correct
		# changes PYTHONPATH changes for this to work (before contentsearch grew 
		# those deps); now it just generates exceptions, so we don't try right now
		start_t = time.time()
		logger.info("Indexing content in-process.")
		for name, extractor in component.getUtilitiesFor(IRenderedBookIndexer):
			logger.info("Indexing %s content", name)
			extractor.transform(book, jobname)
		elapsed = time.time() - start_t
		logger.info("Content indexing took %s(s)", elapsed)
		
	logger.info("Creating JSONP content")
	jsonpbuilder.transform(book)

	logger.info("Creating an archive file")
	archive.create_archive(book, name=jobname)

def render(document, rname, db):
	# Apply renderer
	renderer = createResourceRenderer(rname, db, unmix=False)
	renderer.render(document)
	return renderer

def toXml(document, jobname):
	outfile = '%s.xml' % jobname
	with open(outfile, 'w') as f:
		f.write(document.toXML().encode('utf-8'))

def write_dc_metadata(document, jobname):
	"""
	Write an XML file containing the DublinCore metadata we can extract for this document.
	"""
	mapping = {}
	metadata = document.userdata

	logger.info("Writing DublinCore Metadata.")

	if 'author' in metadata:
		# latex author and DC Creator are both arrays
		mapping['Creator'] = [x.textContent for x in metadata['author']]

	if 'title' in metadata:
		# DC Title is an array, latex title is scalar
		# Sometimes title may be a string or it may be a TeXElement, depending
		# on what packages have dorked things up
		mapping['Title'] = (getattr(metadata['title'], 'textContent', 
							metadata['title']),)

	# The 'date' command in latex is free form, which is not
	# what we want for DC...what do we want?

	# For other options, see zope.dublincore.dcterms.name_to_element
	# Publisher, in particular, would be a good one
	if not mapping:
		return

	xml_string = unicode(zope.dublincore.xmlmetadata.dumpString(mapping))
	with open('dc_metadata.xml', 'w') as f:
		f.write(xml_string.encode('utf-8'))

def generateImages(document):
	## Generates required images ###
	## Replace this with configuration/use of ZCA?
	OVERRIDE_INDEX_NAME = getattr(ResourceTypeOverrides, 'OVERRIDE_INDEX_NAME')
	local_overrides = os.path.join(os.getcwd(), '../nti.resourceoverrides')
	if os.path.exists(os.path.join(local_overrides, OVERRIDE_INDEX_NAME)):
		overrides = local_overrides
	else:
		overrides = resource_filename(__name__, 'resourceoverrides')
	db = ResourceDB(document, overridesLocation=overrides)
	db.generateResourceSets()
	return db
