#!/usr/bin/env python2.7

from zope import interface

import os
import xml.dom.minidom as minidom
import urllib

from . import interfaces

__all__ = ('Library', 'LibraryEntry', 'TOCEntry')

TOC_FILENAME = 'eclipse-toc.xml'

def _TOCPath( path ):
	return os.path.join( path, TOC_FILENAME )

def _hasTOC( path ):
	""" Does the given path point to a directory containing a TOC file?"""
	return os.path.exists( _TOCPath( path ) )

class TOCEntry(object):

	def __init__( self ):
		self._children = None
		self.parent = None

	def appendChild( self, child ):
		if not self._children:
			self._children = [child]
		else:
			self._children.append( child )

	@property
	def children(self):
		return self._children if self._children else ()

	def __str__(self):
		return str(self.__dict__)

	def pathToPropertyValue( self, prop, value ):
		if getattr( self, prop, None ) == value:
			return [self]
		for child in self.children:
			childPath = child.pathToPropertyValue( prop, value )
			if childPath:
				childPath.append( self )
				if not self.parent:
					childPath.reverse()
				return childPath
		return None


class LibraryEntry(object):
	""" Contains values like href for externalization, also contains
	localPath which is a reference to the complete path on the local
	filesystem of the directory this object represents."""

	def __init__(self, extItems=None, localPath=None):
		super(LibraryEntry,self).__init__()
		self.extItems = {}
		self.localPath = localPath
		if extItems:
			self.extItems.update( extItems )

	def toExternalObject( self ):
		return self.extItems

	# Make this object like a dictionary
	# and also make the external object properties visible as
	# read-only attributes on this object.
	def __getitem__(self,key):
		try:
			return self.extItems[key]
		except KeyError:
			return self.__dict__[key]

	def __getattr__(self, name):
		# @property does not play well with custom __getattr__
		if name == 'toc':
			return self._toc()
		try:
			return self.extItems[name]
		except KeyError:
			raise AttributeError( name )

	def _tocItem( self, node ):
		tocItem = TOCEntry()
		for i in ('NTIRelativeScrollHeight', 'href', 'icon', 'label', 'ntiid'):
			setattr( tocItem, i, node.getAttribute( i ) )

		for child in [x for x in node.childNodes
					  if x.nodeType == x.ELEMENT_NODE and x.tagName == 'topic']:
			child = self._tocItem( child )
			child.parent = tocItem
			tocItem.appendChild( child )
		return tocItem

	def _toc(self):
		""" Returns the table-of-contents tree for this entry,
		if it exists on the local filesystem. Otherwise returns None."""
		if not _hasTOC( self.localPath ): return None
		dom = minidom.parse( _TOCPath( self.localPath ) )
		return self._tocItem( dom.firstChild )

	def pathToPropertyValue( self, prop, value ):
		toc = self.toc
		return toc.pathToPropertyValue( prop, value )


class Library(object):

	interface.implements(interfaces.ILibrary)

	def __init__(self, paths=() ):
		"""
		Creates a library that will examine the given paths.

		:param paths: A sequence of strings or tuples. If a string,
			it is a path to a location of a library entry on the
			filesystem. If a tuple, it begins with that path (or None)
			followed by a boolean saying whether to ignore the existence
			of the directory on the filesystem and create a mock
			LibraryEntry. An optional third entry is the title; if missing
			it will be the directory name. An optional fourth entry is the
			relative path to the icon. In other words:
			`(path, even_if_not_found, [Title], [relative icon path])`

		EOD
		"""
		self.paths = paths

	@property
	def icon(self):
		return '/prealgebra/icons/chapters/Chalkboard.tif'

	@property
	def title(self):
		return 'Library'

	@property
	def titles(self):
		""" Returns a sequence of LibraryEntry items. """
		titles = []
		for pathEntry in self.paths:

			path = pathEntry
			overridePath = False
			title = None
			iconPath = None
			if isinstance( pathEntry, tuple ):
				path = pathEntry[0]
				overridePath = pathEntry[1] if len(pathEntry) > 1 else False
				title = pathEntry[2] if len(pathEntry) > 2 else None
				iconPath = pathEntry[3] if len(pathEntry) > 3 else None

			if overridePath or _hasTOC( path ):
				if _hasTOC( path ):
					path = os.path.abspath( path )

				installable = True
				installtime = -1

				archiveFile = os.path.join( path, 'archive.zip' )
				installable = os.path.exists( archiveFile )
				if installable:
					installtime = os.stat( archiveFile )[os.path.stat.ST_MTIME]

				base = os.path.split( path )[-1]
				if not title:
					title = base.title()
				base = '/' + base
				if not iconPath:
					iconPath = base + '/icons/' + title + '-Icon.png'
				elif not iconPath.startswith( base ):
					iconPath = (base + iconPath if iconPath[0] == '/' else base + '/' + iconPath)

				online = { 'icon': urllib.quote( iconPath ),
						   'href': urllib.quote( base ) + '/index.html',
						   'root': urllib.quote( base ) + '/',
						   'index': urllib.quote( base ) + '/' + TOC_FILENAME,
						   'title': title,
						   'installable': installable,
						   'version': '1.0' }

				if installable:
					online['archive'] = urllib.quote(base) + '/archive.zip'
					online['Archive Last Modified'] = installtime
				entry = LibraryEntry( online )
				entry.localPath = path
				titles.append( entry )

		return titles

	def __getitem__( self, key ):
		"""
		:return: The LibraryEntry having a name or ntiid that matches `key`.
		"""
		for title in self.titles:
			if key == title.title or (title.toc and title.toc.ntiid == key):
				return title
		raise KeyError( key )

	def toExternalObject( self ):
		return { 'icon': self.icon,
				 'title': self.title,
				 'titles' : [x.toExternalObject() for x in self.titles] }

	def pathToNTIID(self, ntiid):
		""" Returns a list of TOCEntry objects in order until
		the given ntiid is encountered, or None of the id cannot be found."""
		for title in self.titles:
			result = title.pathToPropertyValue( 'ntiid', ntiid )
			if result:
				return result
		return None

	def childrenOfNTIID( self, ntiid ):
		""" Returns a flattened list of all the children entries of ntiid
		in no particular order. If there are no children, returns []"""
		path = self.pathToNTIID( ntiid )
		result = []
		if path:
			parent = path[-1]
			def rec(toc,accum):
				for child in toc.children:
					rec( child, accum )
				accum.append( toc )
			rec( parent, result )
			# And the last thing we did was append the parent
			# itself, so take it off; we only want the children
			result.pop()
		return result
