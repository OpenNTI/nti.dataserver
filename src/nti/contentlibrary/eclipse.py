#!/usr/bin/env python
"""
Objects for working with Eclipse index representations of content packages.
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import os
import xml.dom.minidom as minidom
# Sadly, minidom doesn't have its own exceptions
# and doesn't document what it throws. Thus
# only by trial and error do we know it's using xml.sax.expat
from xml.parsers.expat import ExpatError

from . import contentunit

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

def _tocItem( node, dirname, factory=contentunit.FilesystemContentUnit ):
	tocItem = factory()
	for i in ('NTIRelativeScrollHeight', 'href', 'icon', 'label', 'ntiid'):
		setattr( tocItem, i, node.getAttribute( i ) )

	tocItem.filename = os.path.join( dirname, tocItem.href )

	children = []
	ordinal = 1
	for child in [x for x in node.childNodes
				  if x.nodeType == x.ELEMENT_NODE and x.tagName == 'topic']:
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
		dom = minidom.parse( _TOCPath( localPath ) )
	except (IOError,ExpatError):
		logger.debug( "Failed to parse TOC at %s", localPath, exc_info=True )
		return None
	content_package = _tocItem( dom.firstChild, localPath, factory=contentunit.FilesystemContentPackage )
	content_package.root = os.path.basename( localPath )
	content_package.index = os.path.basename( _TOCPath( localPath ) )

	archive = os.path.join( localPath, ARCHIVE_FILENAME )
	if os.path.exists( archive ):
		content_package.archive = ARCHIVE_FILENAME
		content_package.installable = True

	return content_package
