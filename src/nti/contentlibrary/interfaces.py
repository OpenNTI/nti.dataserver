#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.annotation.interfaces import IAnnotatable
from zope.dublincore import interfaces as dub_interfaces
from zope.location.interfaces import IContained as IZContained

from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from nti.dublincore.interfaces import ILastModified
from nti.dublincore.interfaces import IDCOptionalDescriptiveProperties

from persistent.interfaces import IPersistent

from nti.schema.field import Number
from nti.schema.field import ValidTextLine as TextLine
from nti.schema.field import IndexedIterable
from nti.schema.field import Iterable
from nti.schema.field import Object
from nti.schema.field import Int
from nti.schema.field import Bool

# pylint: disable=E0213,E0211

### Hierarchy abstraction

# TODO: I'm not happy with the way paths are handled. How can the 'relative'
# stuff be done better? This is mostly an issue with the IContentPackage and its 'root'
# attribute. That's mostly confined to externalization.py now.

# The IDelimitedHierarchy objects are part of an attempt to deal with this.
# All of the string properties that contain relative paths are
# considered deprecated

class IDelimitedHierarchyItem(IZContained):
	"""
	The __parent__ of the bucket should be the containing bucket;
	it *should* be aliased to the ``bucket`` property.
	"""
	name = TextLine(title="The name of this bucket;"
					" __name__ is an alias.")


class IDelimitedHierarchyBucket(IDelimitedHierarchyItem):
	"""
	An item representing a container, like a folder.
	"""

class IEnumerableDelimitedHierarchyBucket(IDelimitedHierarchyBucket):
	"""
	A bucket that can be enumerated to produce its
	children keys and buckets.
	"""

	def enumerateChildren():
		"""
		Return an iterable of child buckets and keys.
		"""

class IDelimitedHierarchyKey(IDelimitedHierarchyItem):
	"""
	An item representing a leaf node.
	"""

	bucket = Object(IDelimitedHierarchyBucket,
					title="The bucket to which this key is relative;"
					" __parent__ is an alias.",
					default=None,
					required=False)



class IContentPackageEnumeration(interface.Interface):
	"""
	Something that can enumerate content packages,
	but does not need to provide any interpretation of
	those packages; that's left to the library.

	This is an abstraction layer to separate possible content packages
	from those actually contained in a library.

	For persistence, these enumerations will often reduce
	to a function that uses a global utility to find themselves;
	in this way they can be semi-independent of the data in the database
	and configuration changes.

	For enumerations that have a way of recording when their
	contents change, they may optionally implement the
	:class:`ILastModified` interface.
	"""

	def enumerateContentPackages():
		"""
		Return an iterable of content packages. These packages
		are not considered to have been created or stored within
		a library yet, so they should have no ``__parent__``
		and no created or added events should be fired for them.

		The contents of this enumeration may change over time.
		"""

class IDelimitedHierarchyContentPackageEnumeration(IContentPackageEnumeration):
	"""
	An enumeration that works by inspecting a particular bucket.
	"""

	root = Object(IEnumerableDelimitedHierarchyBucket,
					title="The bucket that will be introspected for content",
					default=None,
					required=True)

	def childEnumeration(name):
		"""
		Return a new object that would enumerate objects found within
		the given named bucket.
		"""

class IContentPackageLibrary(ILastModified,
							 IZContained):
	"""
	A library or catalog of all available packages of content.

	When content packages are examined and before they are
	added to the library it is expected that compliant
	implementations will broadcast :class:`zope.lifecycleevent.IObjectCreatedEvent`,
	and when they are actually added to the library an :class:`zope.lifecycleevent.IObjectAddedEvent`
	should be broadcast. Note that only certain library implementations are
	compliant with this protocol.

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

	contentPackages = Iterable(title=u'Sequence of all known :class:`IContentPackage`')

class ISyncableContentPackageLibrary(IContentPackageLibrary):
	"""
	A library that relies on external information and must be
	synchronized in order to have an accurate ``contentPackages``
	value.
	"""

	def syncContentPackages():
		"""
		Do whatever is necessary to sync content packages.

		If this is done, and the sync results in a change, this
		should fire an :class:`IContentPackageLibrarySynchedEvent`.
		By the time this event is fired, any added/removed/modified
		events for individual content packages will have been fired.
		"""

class IContentPackageLibrarySynchedEvent(IObjectModifiedEvent):
	"""
	An event fired when a content package library has completed
	a synchronization that resulted in changes. This is fired
	after events for individual content package changes.
	"""

@interface.implementer(IContentPackageLibrarySynchedEvent)
class ContentPackageLibrarySynchedEvent(ObjectModifiedEvent):
	"""
	Content package synced event.
	"""

class IGlobalContentPackageLibrary(ISyncableContentPackageLibrary):
	"""
	A non-persistent content library that needs to be synchronized
	on every startup.
	"""

class IPersistentContentPackageLibary(IPersistent,
									  ISyncableContentPackageLibrary):
	"""
	A content library whose contents are expected to persist
	and which needs synchronization only when external
	contents have changed.

	.. warning:: Even though the packages and units that are
		contained within this library may be persistent, because
		libraries may be arranged in a hierarchy of persistent
		and non-persistent libraries, you should never attempt to
		store a persistent reference to a library entry. Instead,
		store its NTIID and always use the current library to
		retrieve the item. Implementations of :class:`.IWeakRef`
		are provided for this purpose.
	"""

class IDisplayablePlatformPresentationResources(interface.Interface):
	"""
	A (pointer to s) set of resources for presentation on a specific platform.
	"""

	PlatformName = TextLine(title="The name of the platform this package is meant for.")
	InheritPlatformName = TextLine(title="A platform to inherit from",
								   description="If present, this object should merge missing resources "
								   "from this named platform.")
	# XXX: Fill in missing to match disk layout

class IDisplayableContent(IZContained,
						  IDCOptionalDescriptiveProperties,
						  dub_interfaces.IDCExtended):
	"""
	Something that is meant to be displayed as a top-level object to an end user.

	Note that we inherit ``description`` and ``title`` from the Dublin
	interfaces.
	"""

	PlatformPresentationResources = Iterable(title="Sequence of the presentations for this content.",
											 default=(),
											 required=False)


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

	key = Object(IDelimitedHierarchyKey,
				 title="The key designating this entry in the hierarchy.",
				 default=None)

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

class IContentUnit(IZContained,
				   IDCOptionalDescriptiveProperties,
				   IAnnotatable):
	"""
	One identified unit of content.

	The ``__parent__`` of this object will be the containing content unit, which
	will ultimately be the :class:`IContentPackage`; the containing unit of the package
	will be the :class:`IContentPackageLibrary`.
	"""
	ordinal = Int(title="The number (starting at 1) representing which nth child of the parent I am.",
				  default=1, min=1)
	href = TextLine(title="DEPRECATED URI for the representation of this item.",
					description="If this unit is within a package, then this is potentially a relative path",
					default='')
	key = Object(IDelimitedHierarchyKey,
				 title="URI for the representation of this item",
				 default=None)
	ntiid = TextLine(title="The NTIID for this item",
					 default=None,
					 required=False)
	icon = Object(IDelimitedHierarchyKey,
				  title="URI for an image for this item, typically specially designed",
				  required=False,
				  default=None)
	thumbnail = Object(IDelimitedHierarchyKey,
					   title="URI for a thumbnail for this item, typically auto-generated",
					   required=False,
					   default=None)
	children = Iterable(title="Any :class:`IContentUnit` objects this item has.",
						default=())

	embeddedContainerNTIIDs = IndexedIterable(title="An iterable of NTIIDs of sub-containers embedded via reference in this content",
											  value_type=TextLine(title="The embedded NTIID"),
											  unique=True,
											  default=())

class IContentPackage(IContentUnit,
					  IDisplayableContent,
					  ILastModified):
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

	root = Object(IDelimitedHierarchyItem,
				  title="Path portion of a uri for this object.",
				  default=None)
	index = Object(IDelimitedHierarchyKey,
				   title="Path portion to an XML file representing this content package",
				   default=None,
				   required=False)
	index_jsonp = Object(IDelimitedHierarchyKey,
						 title="Optional location of a JSONP version of the index.",
						 required=False,
						 default=None)
	index_last_modified = Number(title="Time since the epoch the index for this package was last modified.",
								 description="This is currently the best indication of when this package as a whole may have changed.",
								 readonly=True,
								 default=-1 )
	installable = Bool(title="Whether or not this content package can be installed locally (offline)",
					   default=False)
	archive = TextLine(title="DEPRECATED. If this content is installable, this is the relative path to a ZIP archive of the content",
					   default=None,
					   required=False)
	archive_unit = Object(IContentUnit,
						  title="A child object representing the ZIP archive.",
						  default=None,
						  required=False)
	renderVersion = Int(title="Version of the rendering process that produced this package.",
							   default=1,
						min=1)

class IPersistentContentUnit(IPersistent, IContentUnit):
	"""
	A persistent content unit.


	.. warning:: See the warning on the persistent content package
		library about references to these items. In short, always
		store them by NTIID and use the current library to look them
		up; implementations of :class:`.IWeakRef` are provided
		for this purpose.
	"""

class IPersistentContentPackage(IPersistentContentUnit, IContentPackage):
	"""
	A persistent content package.
	"""

class IPotentialLegacyCourseConflatedContentPackage(IContentPackage):
	"""
	A legacy property that should be available on all content packages.
	"""

	isCourse = Bool(title="If this package is for a course",
						   default=False,
						   required=True)

class ILegacyCourseConflatedContentPackage(IPotentialLegacyCourseConflatedContentPackage):
	"""
	Legacy properties from when we treated courses as simply a set
	of attributes on content.

	This is all deprecated but exists to distinguish these things.
	"""

	# Course support
	# ALL OF THIS IS DEPRECATED
	isCourse = Bool(title="If this package is for a course",
						   default=False,
						   required=True)
	courseName = TextLine(title="Course name",
						   required=True)
	courseTitle = TextLine(title="Course title",
						   required=True)
	courseInfoSrc = TextLine(title="The relative path to a JSON file",
							 description="This should be a IDelimitedHierarchyKey, but isn't; Assume it is a sibling",
							 required=True,
							 default='')

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


class IFilesystemBucket(IEnumerableDelimitedHierarchyBucket):
	"""
	An absolute string of a filesystem directory.
	"""

	absolute_path = TextLine(title="The absolute path on disk of the directory")


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

class IPersistentFilesystemContentUnit(IPersistentContentUnit, IFilesystemContentUnit):
	pass

class IPersistentFilesystemContentPackage(IPersistentContentPackage, IFilesystemContentPackage):
	pass

class IFilesystemContentPackageLibrary(IContentPackageLibrary):
	"""
	A content package library based on reading the contents of the filesystem.
	"""

class IPersistentFilesystemContentPackageLibrary(IPersistentContentPackageLibary,
												 IFilesystemContentPackageLibrary):
	pass

class IGlobalFilesystemContentPackageLibrary(IGlobalContentPackageLibrary,
											 IFilesystemContentPackageLibrary):
	pass

###
# Content bundles
###
class IContentPackageBundle(IDisplayableContent):
	pass

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

class IContentUnitAnnotationUtility(IZContained):
	"""
	Stores annotations for content units.
	"""

	def getAnnotations(content_unit):
		"""
		Returns an :class:`.IAnnotations` for the content unit.
		"""

	def getAnnotationsById(ntiid):
		"""
		Returns :class:`.IAnnotations` for the NTIID of the content unit.
		"""

	def hasAnnotations(content_unit):
		"""
		Returns a truthful value indicating whether the given content
		unit has annotations.
		"""

class ISiteLibraryFactory(interface.Interface):

	def library_for_site_named(name):
		pass
