#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import schema
from zope.location.interfaces import IContained as IZContained
from zope.dublincore import interfaces as dub_interfaces

from nti.utils.schema import Number, ValidTextLine as TextLine
from nti.utils.schema import IndexedIterable
from nti.utils.schema import Object

# pylint: disable=E0213,E0211

class IContentPackageLibrary(interface.Interface):
	"""
	A library or catalog of all available packages of content.
	"""

	def pathToNTIID(ntiid):
		"""
		Returns a list of :class:`IContentUnit` objects in order until
		the given NTIID is encountered, or :obj:`None` if the ``ntiid`` cannot be found.

		.. attention:: This does not include the
			:const:`nti.ntiids.ntiids.ROOT` NTIID. That is an implicit
			element before the first element in the returned sequence.

		.. caution:: Passing the root NTIID will result in a return of None.
		"""

	def childrenOfNTIID(ntiid):
		""" Returns a flattened list of all the children entries of ntiid
		in no particular order. If there are no children, returns ``[]``"""

	def pathsToEmbeddedNTIID(ntiid):
		"""
		Returns a list of paths (sequences of :class:`IContentUnit` objects); the last
		element in each path is a :class:`IContentUnit` that contains an
		embedded reference to the given NTIID. That is, the returned list
		describes all the locations that the NTIID is known to be referenced
		for use as a subcontainer.

		The returned list of paths is in no particular order. If no embedding locations
		are known, returns an empty iterable.
		"""

	def __getitem__(key):
		"""
		Return the :class:`IContentUnit` having the matching ``title`` or ``ntiid``.
		(Support for titles is a convenience and not to be relied upon).
		"""

	def get(key, default=None):
		"""
		See :meth:`__getitem__`
		"""

	def __contains__(key):
		"Consistent with :meth:`__getitem__`"

	def __len__():
		"The number of content packages in this library"

	contentPackages = schema.Iterable(title=u'Sequence of all known :class:`IContentPackage`')

	lastModified = Number(title="Best estimate of the last time this library and its contents was modified",
						  readonly=True)

# TODO: I'm not happy with the way paths are handled. How can the 'relative'
# stuff be done better? This is mostly an issue with the IContentPackage and its 'root'
# attribute. That's mostly confined to externalization.py now.

# The IDelimitedHierarchy objects are part of an attempt to deal with this.
# All of the string properties that contain relative paths are
# considered deprecated

class IDelimitedHierarchyBucket(IZContained):
	name = TextLine(title="The name of this bucket")

class IDelimitedHierarchyKey(IZContained):

	bucket = Object(IDelimitedHierarchyBucket, title="The bucket to which this key is relative.")
	name = TextLine(title="The relative name of this key. Also in `key` and `__name__`.")

class IDelimitedHierarchyEntry(interface.Interface, dub_interfaces.IDCTimes):
	"""
	Similar to an :class:`IFilesystemEntry`, but not tied to the local (or mounted)
	filesystem. Each entry is named by a ``/`` delimited key analogous to a filesystem
	path, but those keys are not necessarily usable with the functions of :mod:`os.path`,
	and the relative expense of operations may not be the same.

	The primary reason for this interface is as a facade supporting both local
	filesystem storage and Amazon S3 (:mod:`boto.s3`) storage.

	The ``__parent__`` of this entry should be an :class:`IDelimitedHierarchyEntry` representing
	its parent in the tree and having the same ``key`` as :meth:`get_parent_key`. Note
	that this interface is commonly mixed-in with :class:`IContentUnit` which also defines
	the ``__parent__`` attribute.
	"""

	key = Object(IDelimitedHierarchyKey, title="The key designating this entry in the hierarchy.")

	def get_parent_key():
		"""
		Return the parent key in the hierarchy, if there is one. Otherwise returns None.
		"""

	def read_contents():
		"""
		Read and return, as a sequence of bytes, the contents of this entry.

		:return: Either the byte string of the contents of the entry, or if there is no such entry,
		`None`.
		"""

	def make_sibling_key(sibling_name):
		"""
		Create a value suitable for use as the ``key`` attribute of this or a similar
		object having the given `sibling_name`.
		"""

	def read_contents_of_sibling_entry(sibling_name):
		"""
		Read and return, as a sequence of bytes, the contents of an entry in the same
		level of the hierarchy as this entry.

		:param string sibling_name: The local, undelimited, name of a sibling entry (e.g., ``foo.txt``).

		:return: Either the byte string of the contents of the entry, or if there is no such entry,
		`None`.

		"""

	def does_sibling_entry_exist(sibling_name):
		"""
		Ask if the sibling entry named by `sibling_name` exists. Returns a true value
		if it does, a false value if it doesn't.
		"""


class IContentUnit(IZContained, dub_interfaces.IDCDescriptiveProperties):
	"""
	One identified unit of content.

	The ``__parent__`` of this object will be the containing content unit, which
	will ultimately be the :class:`IContentPackage`; the containing unit of the package
	will be the :class:`IContentPackageLibrary`.
	"""
	ordinal = schema.Int(title="The number (starting at 1) representing which nth child of the parent I am.")
	href = TextLine(title="DEPRECATED URI for the representation of this item.",
					description="If this unit is within a package, then this is potentially a relative path")
	key = Object(IDelimitedHierarchyKey,
				 title="URI for the representation of this item")
	ntiid = TextLine(title="The NTIID for this item")
	title = TextLine(title="The human-readable section name of this item; alias for `__name__`")  # also defined by IDCDescriptiveProperties
	icon = Object(IDelimitedHierarchyKey,
				  title="URI for an image for this item, typically specially designed",
				  required=False,
				  default=None)
	thumbnail = Object(IDelimitedHierarchyKey,
					   title="URI for a thumbnail for this item, typically auto-generated",
					   required=False,
					   default=None)
	children = schema.Iterable(title="Any :class:`IContentUnit` objects this item has.")

	embeddedContainerNTIIDs = IndexedIterable(title="An iterable of NTIIDs of sub-containers embedded via reference in this content",
											  value_type=TextLine(title="The embedded NTIID"),
											  unique=True)

class IContentPackage(IContentUnit, dub_interfaces.IDCExtended):
	"""
	An identified collection of content treated as a unit.
	The package starts with a root unit (this object).

	Typically, this object's ``href`` attribute will end in ``index.html``. The
	:class:`IContentUnit` objects that reside as children within this object
	will usually have ``href`` and ``icon`` attributes that are relative to this
	object's ``root`` (if they are not absolute URLs).

	.. note:: The ``root`` attribute should be considered deprecated, as should
	all resolving of content relative to it. It will probably be becoming
	a :class:`IDelimitedHierarchyEntry` object when that stabilizes more.
	In subintefaces that are :class:`IDelimitedHierarchyEntry`, the root
	becomes an alias for :meth:`IDelimitedHierarchyEntry.get_parent_key`.
	"""

	root = Object(IDelimitedHierarchyKey,
				  title="Path portion of a uri for this object.")
	index = Object(IDelimitedHierarchyKey,
				   title="Path portion to an XML file representing this content package")
	index_jsonp = Object(IDelimitedHierarchyKey,
						 title="Optional location of a JSONP version of the index.",
						 required=False,
						 default=None)

	index_last_modified = Number(title="Time since the epoch the index for this package was last modified.",
								 description="This is currently the best indication of when this package as a whole may have changed.",
								 readonly=True)
	installable = schema.Bool(title="Whether or not this content package can be installed locally (offline)")
	archive = TextLine(title="DEPRECATED. If this content is installable, this is the relative path to a ZIP archive of the content",
					   default=None,
					   required=False)
	archive_unit = Object(IContentUnit,
						  title="A child object representing the ZIP archive.",
						  default=None,
						  required=False)
	renderVersion = schema.Int(title="Version of the rendering process that produced this package.",
							   default=1, min=1)
	
	# Course support
	isCourse = schema.Bool(title="If this package is for a course.", default=False, required=False)
	courseName = TextLine(title="Course name.", required=False)

class IDelimitedHierarchyContentUnit(IContentUnit, IDelimitedHierarchyEntry):
	"""
	The unification of :class:`IContentUnit` and :class:`IDelimitedHierarchyEntry`, to make writing adapters
	easier. All content units provided by this package will implement this interface.
	"""

class IDelimitedHierarchyContentPackage(IContentPackage, IDelimitedHierarchyContentUnit):
	"""
	The unification of :class:`IContentPackage` and :class:`IDelimitedHierarchyEntry`, to make writing adapters
	easier. All content packages provided by this package will implement this interface.
	"""

class IS3Bucket(IDelimitedHierarchyBucket):  # .boto_s3 will patch these to be IZContained
	"""
	See :class:`boto.s3.bucket.Bucket`.

	.. note:: This should define a subset of things we want to use, hopefully
	compatible with both :mod:`boto.s3.bucket` and :mod:`boto.file.bucket`.
	"""

	name = TextLine(title="The name of this bucket; globally unique")

class IS3Key(IDelimitedHierarchyKey):
	"""
	See :class:`boto.s3.key.Key`.

	.. note:: This should define a subset of things we want to use, hopefully
		compatible with both :mod:`boto.s3.bucket` and :mod:`boto.file.bucket`.
	"""

	bucket = Object(IS3Bucket, title="The bucket to which this key belongs")

	name = TextLine(title="The name of this key; unique within the bucket; `__name__` and `key` are aliases")

class IS3ContentUnit(dub_interfaces.IDCTimes, IDelimitedHierarchyContentUnit):

	key = Object(IS3Key, title="The key identifying the unit of content this belongs to.")
	# @deprecated: Prefer IDCTimes
	lastModified = Number(title="Time since the epoch this unit was last modified.",
					  	  readonly=True)

class IS3ContentPackage(IDelimitedHierarchyContentPackage, IS3ContentUnit):
	pass


class IFilesystemBucket(IDelimitedHierarchyBucket):
	"""
	An absolute string of a filesystem directory.
	"""

	name = TextLine(title="The complete path of this key (same as self); unique within the filesystem; `__name__` and `key` are aliases")


class IFilesystemKey(IDelimitedHierarchyKey):
	"""
	A string, relative to its parent.
	"""

	bucket = Object(IFilesystemBucket, title="The bucket to which this key belongs")

	name = TextLine(title="The name of this key; unique within the bucket; `__name__` and `key` are aliases")

	absolute_path = TextLine(title="The absolute path on disk for this key.")

class IFilesystemEntry(interface.Interface, dub_interfaces.IDCTimes, IDelimitedHierarchyEntry):
	"""
	A mixin interface for things that are backed by items on the filesystem.

	The timestamp values defined here refer to the actual item on the filesystem,
	e.g., the times for the content unit itself.

	"""
	filename = TextLine(title="The absolute path to the file")

	# @deprecated: Prefer IDCTimes
	lastModified = Number(title="Time since the epoch this unit was last modified.",
						  readonly=True)


class IFilesystemContentUnit(IDelimitedHierarchyContentUnit, IFilesystemEntry):
	"""
	A content unit backed by a file on disk.

	The values for the `href` and `filename` attributes will be the same, when the mapping
	between file and content unit is one-to-one. If the mapping is deeper than that, then the
	href attribute may include a fragment identifier but the filename will still be a single
	file.
	"""

class IFilesystemContentPackage(IDelimitedHierarchyContentPackage, IFilesystemEntry):
	"""
	A content package backed by a file on disk.

	The `root` attribute can be derived from the :func:`os.path.dirname` of the
	`filename` attribute.
	"""

class IFilesystemContentPackageLibrary(IContentPackageLibrary):
	"""
	A content package library based on reading the contents of the filesystem.
	"""

class IContentUnitHrefMapper(interface.Interface):
	"""
	Register these as adapters to produce the best HREF value for a given content
	unit in URL space.

	.. note:: This isn't quite the right concept or right idea. This should probably
	be combined somehow with ILink, and/or made more specific. You may
	want to register these as multi-adapters depending on the current request.
	"""
	href = interface.Attribute("The best HREF, something a client can resolve.")

class IAbsoluteContentUnitHrefMapper(IContentUnitHrefMapper):
	"""
	A type of href mapper that produces absolute hrefs, not relative
	to anything, even the host.
	"""
