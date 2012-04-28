#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from zope import interface
from zope import schema
from zope.location.interfaces import IContained as IZContained

#pylint: disable=E0213,E0211



class IContentPackageLibrary(interface.Interface):
	"""
	A library or catalog of all available packages of content.
	"""

	def pathToNTIID(ntiid):
		""" Returns a list of :class:IContentCollection objects in order until
		the given ntiid is encountered, or None if the id cannot be found."""

	def childrenOfNTIID( ntiid ):
		""" Returns a flattened list of all the children entries of ntiid
		in no particular order. If there are no children, returns []"""

	def __getitem__( key ):
		"""
		Return the ILibraryEntry having the matching `title` or `ntiid`.
		(Support for titles is a convenience and not to be relied upon).
		"""

	contentPackages = schema.Iterable( title=u'Sequence of :class:`IContentPackage`')

# TODO: I'm not happy with the way paths are handled. How can the 'relative'
# stuff be done better? This is mostly an issue with the IContentPackage,


class IContentUnit(IZContained):
	"""
	One identified unit of content.
	"""
	ordinal = schema.Int( title="The number (starting at 1) representing which nth child of the parent I am." )
	href = schema.TextLine( title="URI for the representation of this item.",
						description="If this unit is within a package, then this is a relative path" )
	ntiid = schema.TextLine( title="The NTIID for this item" )
	title = schema.TextLine( title="The human-readable section name of this item; alias for `__parent__`" )
	icon = schema.TextLine( title="URI for an image for this item, or None" )
	children = schema.Iterable( title="Any :class:`IContentUnit` objects this item has." )


class IContentPackage(IContentUnit):
	"""
	An identified collection of content treated as a unit.
	The package starts with a root unit (this object).

	Typically, this object's `href` attribute will end in `index.html`. The
	:class:`IContentUnit` objects that reside as children within this object
	will usually have `href` and `icon` attributes that are relative to this
	object's `root`.
	"""

	root = interface.Attribute( "Path portion of a uri for this object" )
	index = schema.TextLine( title="Path portion to an XML file representing this content package" )
	installable = schema.Bool( title="Whether or not this content package can be installed locally (offline)" )
	archive = schema.TextLine( title="If this content is installable, this is the relative path to a ZIP archive of the content" )


class IFilesystemEntry(interface.Interface):
	"""
	A mixin interface for things that are backed by items on the filesystem.
	"""
	filename = schema.TextLine( title="The absolute path to the file" )

class IFilesystemContentUnit(IContentUnit,IFilesystemEntry):
	"""
	A content unit backed by a file on disk.

	The values for the `href` and `filename` attributes will be the same.
	"""

class IFilesystemContentPackage(IContentPackage,IFilesystemEntry):
	"""
	A content package backed by a file on disk.

	The `root` attribute can be derived from the :func:`os.path.dirname` of the
	`filename` attribute.
	"""
