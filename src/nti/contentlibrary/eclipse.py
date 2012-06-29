#!/usr/bin/env python
"""
Objects for working with Eclipse index representations of content packages.
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import os
from lxml import etree
from . import contentunit

# some direct imports for speed
from os.path import join as path_join
from .contentunit import FilesystemContentUnit, FilesystemContentPackage

__all__ = ('Library', 'LibraryEntry', 'TOCEntry')

TOC_FILENAME = 'eclipse-toc.xml'
ARCHIVE_FILENAME = 'archive.zip'

def _TOCPath( path ):
	return os.path.abspath( os.path.join( path, TOC_FILENAME ))

def _hasTOC( path ):
	""" Does the given path point to a directory containing a TOC file?"""
	return os.path.exists( _TOCPath( path ) )

def _isTOC( path ):
	return os.path.basename( path ) == TOC_FILENAME

_toc_item_attrs = ('NTIRelativeScrollHeight', 'href', 'icon', 'label', 'ntiid')

def _tocItem( node, dirname, factory=FilesystemContentUnit ):
	tocItem = factory()
	for i in _toc_item_attrs:
		setattr( tocItem, i, node.get( i ) )

	tocItem.filename = path_join( dirname, tocItem.href )

	children = []
	ordinal = 1
	for child in node.iterchildren(tag='topic'):
		child = _tocItem( child, dirname )
		child.__parent__ = tocItem
		child.ordinal = ordinal; ordinal += 1
		children.append( child )

	tocItem.children = children
	return tocItem

def EclipseContentPackage( localPath ):
	"""
	Given a path to an eclipse TOC file, or a directory containing one,
	parse and return the TOC as a :class:`IFilesystemContentPackage`.

	If parsing fails, returns None.
	"""
	if _isTOC( localPath ):
		localPath = os.path.dirname( localPath )

	if not _hasTOC( localPath ):
		return None

	localPath = os.path.abspath( localPath )
	try:
		dom = etree.parse( _TOCPath( localPath ) )
	except (IOError,ExpatErroretree.Error):
		logger.debug( "Failed to parse TOC at %s", localPath, exc_info=True )
		return None
	root = dom.getroot()
	content_package = _tocItem( root, localPath, factory=FilesystemContentPackage )
	content_package.root = os.path.basename( localPath )
	content_package.index = os.path.basename( _TOCPath( localPath ) )

	renderVersion = root.get( 'renderVersion' )
	if renderVersion:
		content_package.renderVersion = int(renderVersion)

	archive = os.path.join( localPath, ARCHIVE_FILENAME )
	if os.path.exists( archive ):
		content_package.archive = ARCHIVE_FILENAME
		content_package.installable = True

	return content_package
