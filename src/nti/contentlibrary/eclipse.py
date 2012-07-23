#!/usr/bin/env python
"""
Objects for working with Eclipse index representations of content packages.
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import os
from lxml import etree

# some direct imports for speed
from os.path import join as path_join
from .contentunit import FilesystemContentUnit, FilesystemContentPackage

__all__ = ('Library', 'LibraryEntry', 'TOCEntry')

TOC_FILENAME = 'eclipse-toc.xml'
ARCHIVE_FILENAME = 'archive.zip'

def _TOCPath( path ):
	return os.path.abspath( path_join( path, TOC_FILENAME ))

def _hasTOC( path ):
	""" Does the given path point to a directory containing a TOC file?"""
	return os.path.exists( _TOCPath( path ) )

def _isTOC( path ):
	return os.path.basename( path ) == TOC_FILENAME

_toc_item_attrs = ('NTIRelativeScrollHeight', 'href', 'icon', 'label', 'ntiid',)

def _tocItem( node, dirname, factory=FilesystemContentUnit ):
	tocItem = factory()
	for i in _toc_item_attrs:
		setattr( tocItem, i, node.get( i ) )

	setattr( tocItem, 'sharedWith', node.get( 'sharedWith', '' ).split( ' ' ) )
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


def _last_modified( filename ):
	return os.stat( filename )[os.path.stat.ST_MTIME]

# Cache for content packages
# In basic profiling, the cache can provide 3X or more speedups,
# and dramatically reduces the variance
from repoze.lru import LRUCache
import zope.testing.cleanup
_cache = LRUCache( 1000 ) # TODO: Constant for the cache size
zope.testing.cleanup.addCleanUp( _cache.clear )

def EclipseContentPackage( localPath ):
	"""
	Given a path to an eclipse TOC file, or a directory containing one,
	parse and return the TOC as a :class:`IFilesystemContentPackage`.

	If parsing fails, returns None.

	If a TOC node contains a 'sharedWith' attribute, then it is a space separated string
	defining the default value that should be used for sharing within that content if
	no other preference is specified. (See :class:`nti.appserver.interfaces.IContentUnitPreferences`;
	an adapter should be registered.)
	"""
	if _isTOC( localPath ):
		localPath = os.path.dirname( localPath )

	if not _hasTOC( localPath ):
		return None

	localPath = os.path.abspath( localPath )
	toc_path = _TOCPath( localPath )
	try:
		toc_last_modified = _last_modified( toc_path )
		content_package = _cache.get( toc_path )
		if content_package is not None and content_package.index_last_modified <= toc_last_modified:
			return content_package

		dom = etree.parse( _TOCPath( localPath ) )
	except (IOError,etree.Error):
		logger.debug( "Failed to parse TOC at %s", localPath, exc_info=True )
		return None
	root = dom.getroot()
	content_package = _tocItem( root, localPath, factory=FilesystemContentPackage )
	content_package.root = os.path.basename( localPath )
	content_package.index = os.path.basename( _TOCPath( localPath ) )
	content_package.index_last_modified = toc_last_modified

	renderVersion = root.get( 'renderVersion' )
	if renderVersion:
		content_package.renderVersion = int(renderVersion)

	archive = path_join( localPath, ARCHIVE_FILENAME )
	if os.path.exists( archive ):
		content_package.archive = ARCHIVE_FILENAME
		content_package.installable = True

	_cache.put( toc_path, content_package )

	return content_package
