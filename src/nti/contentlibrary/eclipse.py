#!/usr/bin/env python
"""
Objects for working with Eclipse index representations of content packages.
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

from lxml import etree

from zope.dublincore import xmlmetadata

# some direct imports for speed
#from os.path import join as path_join


TOC_FILENAME = 'eclipse-toc.xml'
ARCHIVE_FILENAME = 'archive.zip'
DCMETA_FILENAME = 'dc_metadata.xml'

_toc_item_attrs = ('NTIRelativeScrollHeight', 'href', 'icon', 'label', 'ntiid',)

def _tocItem( node, toc_entry, factory=None, child_factory=None ):
	tocItem = factory()
	for i in _toc_item_attrs:
		setattr( tocItem, i, node.get( i ) )

	if node.get( 'sharedWith', ''):
		tocItem.sharedWith = node.get( 'sharedWith' ).split( ' ' )

	tocItem.key = toc_entry.make_sibling_key( tocItem.href )

	children = []
	ordinal = 1
	for child in node.iterchildren(tag='topic'):
		child = _tocItem( child, toc_entry, factory=child_factory, child_factory=child_factory )
		child.__parent__ = tocItem
		child.ordinal = ordinal; ordinal += 1
		children.append( child )

	tocItem.children = children
	return tocItem

# Cache for content packages
# In basic profiling, the cache can provide 3X or more speedups,
# and dramatically reduces the variance
from repoze.lru import LRUCache
import zope.testing.cleanup
_cache = LRUCache( 1000 ) # TODO: Constant for the cache size
zope.testing.cleanup.addCleanUp( _cache.clear )

def EclipseContentPackage( toc_entry,
						   package_factory=None,
						   unit_factory=None ):
	"""
	Given a :class:`nti.contentlibrary.interfaces.IDelimitedHierarchyEntry` pointing
	to an Eclipse TOC XML file, parse it and return the :class:`IContentPackage`
	tree.

	If parsing fails, returns None.

	If a TOC node contains a 'sharedWith' attribute, then it is a space separated string
	defining the default value that should be used for sharing within that content if
	no other preference is specified. (See :class:`nti.appserver.interfaces.IContentUnitPreferences`;
	an adapter should be registered.)

	:param toc_entry: The hierarchy entry we will use to read the XML from. We make certain
		assumptions about the hierarchy this tree came from, notably that it is only one level
		deep (or rather, it is at least two levels deep and we will be able to access it
		given just the parent entry). (TODO: That property should probably become an IDelimitedHierarchyEntry)
	:param package_factory: A callable of no arguments that produces an :class:`nti.contentlibrary.interfaces.IContentPackage`
	:param unit_factory: A callable of no arguments that cooperates with the `package_factory` and produces
		:class:`nti.contentlibrary.interfaces.IContentUnit` objects that can be part of the content package.
	"""

	try:
		toc_last_modified = toc_entry.lastModified
		content_package = _cache.get( toc_entry.key )
		if content_package is not None and content_package.index_last_modified <= toc_last_modified:
			return content_package

		root = etree.fromstring( toc_entry.read_contents() )
	except (IOError,etree.Error):
		logger.debug( "Failed to parse TOC at %s", toc_entry, exc_info=True )
		return None

	content_package = _tocItem( root, toc_entry, factory=package_factory, child_factory=unit_factory )
	# NOTE: assuming only one level of hierarchy (or at least the accessibility given just the parent)
	# TODO: root and index should probably be replaced with IDelimitedHierarchyEntry objects.
	# NOTE: IDelimitedHierarchyEntry is specified as '/' delimited. This means that when we are working with
	# filesystem objects we have path-dependencies. We won't work on windows
	content_package.root = toc_entry.get_parent_key()
	content_package.index = toc_entry.key
	content_package.index_last_modified = toc_last_modified

	renderVersion = root.get( 'renderVersion' )
	if renderVersion:
		content_package.renderVersion = int(renderVersion)

	if content_package.does_sibling_entry_exist( ARCHIVE_FILENAME ):
		content_package.archive = ARCHIVE_FILENAME
		content_package.installable = True
		content_package.archive_unit = unit_factory( key=content_package.make_sibling_key( ARCHIVE_FILENAME ) )

	dcmetafile_contents = content_package.read_contents_of_sibling_entry( DCMETA_FILENAME )
	if dcmetafile_contents:
		metadata = xmlmetadata.parseString( dcmetafile_contents )
		if 'Creator' in metadata:
			content_package.creators = metadata['Creator']

	_cache.put( toc_entry.key, content_package )

	return content_package
