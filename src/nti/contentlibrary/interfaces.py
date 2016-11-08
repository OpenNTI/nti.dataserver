#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface

from zope.annotation.interfaces import IAnnotatable

from zope.container.constraints import contains  # If passing strings, they require bytes, NOT unicode, or they fail
from zope.container.interfaces import IContentContainer

from zope.dublincore import interfaces as dub_interfaces

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent
from zope.interface.common.sequence import IFiniteSequence

from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectRemovedEvent
from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zope.location.interfaces import IContained as IZContained

from persistent.interfaces import IPersistent

from nti.coremetadata.interfaces import ILastModified

from nti.dataserver_core.interfaces import IShouldHaveTraversablePath

from nti.dublincore.interfaces import IDCOptionalDescriptiveProperties

from nti.ntiids.schema import ValidNTIID

from nti.property.property import alias

from nti.schema.field import Int
from nti.schema.field import Bool
from nti.schema.field import List
from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import Iterable
from nti.schema.field import ValidTextLine
from nti.schema.field import UniqueIterable
from nti.schema.field import IndexedIterable
from nti.schema.field import ValidTextLine as TextLine

# pylint: disable=I0011,E0213,E0211

# Disable pylint warnings about undefined variables, because it catches
# all the __setitem__ and __parent__ in the interfaces.
# pylint: disable=I0011,E0602

# ## Hierarchy abstraction

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

	def getChildNamed(name):
		"""
		If there is a child bucket or key with the given
		name, return it. If there is no such bucket,
		return None. In general, expect case-sensitive
		matching.
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

	def readContents():
		"""
		Return, as a byte-string, the contents of this leaf node.
		"""

	def readContentsAsText(encoding="utf-8"):
		"""
		Return, as a unicode-string, the contents of this leaf node.
		"""

	def readContentsAsJson():
		"""
		Read the contents and return a fresh JSON object (with unicode
		strings). If the contents are not JSON, raises an exception.
		"""

	def readContentsAsETree():
		"""
		Read the contents and return a fresh :mod:`lxml.etree` root node.
		If the contents are not XML, raises an exception.
		"""

	def readContentsAsYaml():
		"""
		Read the contents and return a fresh YAML object (with  unicode
		strings). The contents should define one YAML document; if
		it has more than one the results are undefined.

		YAML (in the version we have) is nearly a superset of JSON,
		but it can load arbitrary python objects, so do not use it on
		untrusted input. Also note that it is likely to be slower than
		JSON (at this writing we don't have libYAML), especially for
		large documents; however, it does support comments and can
		also efficiently support object graphs that reference the same
		(identical) object multiple times.
		"""

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
		Return the :class:`IContentPackage` having the matching ``ntiid``.
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

class ISynchronizationParams(interface.Interface):

	ntiids = IndexedIterable(title="An iterable of NTIIDs of 'things' to sync",
							 value_type=TextLine(title="The NTIID"),
							 unique=True,
							 default=(),
							 required=False)

	allowRemoval = Bool(title="Allow content drops/removal",
					  	default=False,
					  	required=False)

class IGenericSynchronizationResults(interface.Interface):
	pass

class ILibrarySynchronizationResults(IGenericSynchronizationResults):

	Name = TextLine(title="Libray name", required=False)

	Added = List(title="An iterable NTIID of content package added",
				 value_type=TextLine(title="The NTIID"),
				 required=False)

	Modified = List(title="An iterable NTIID of modified content package",
					value_type=TextLine(title="The NTIID"),
					required=False)

	Removed = List(title="An iterable NTIID of content package dropped",
				   value_type=TextLine(title="The NTIID"),
				   required=False)

class IContentPackageSyncResults(IGenericSynchronizationResults):

	Site = ValidTextLine(title="The site name", required=False)

	ContentPackageNTIID = ValidTextLine(title="The ContentPackage NTIID", required=False)

	AssessmentsUpdated =  UniqueIterable(value_type=ValidTextLine(title="An asset NTIID"),
										 title="The updated assessment NTIIDs",
										 default=None, required=False)

	AssessmentsSyncLocked = UniqueIterable(value_type=ValidTextLine(title="An asset NTIID"),
									  	   title="The locked assessment NTIIDs",
									  	   default=None, required=False)

	AssetsUpdated =  UniqueIterable(value_type=ValidTextLine(title="An asset NTIID"),
									title="The updated asset NTIIDs",
									default=None, required=False)

	AssetsSyncLocked = UniqueIterable(value_type=ValidTextLine(title="An asset NTIID"),
									  title="The locked asset NTIIDs",
									  default=None, required=False)

	def add_assessment(item, locked=False):
		"""
		Add an assessment sync result
		"""

	def add_asset(item, locked=False):
		"""
		Add an asset sync result
		"""

class ISynchronizationResults(IFiniteSequence):

	Items = IndexedIterable(title="An iterable of sync results",
							value_type=Object(IGenericSynchronizationResults),
							required=False)

	def add(item):
		"""
		Add a sync result
		"""
	append = add # alias

class ISyncableContentPackageLibrary(IContentPackageLibrary):
	"""
	A library that relies on external information and must be
	synchronized in order to have an accurate ``contentPackages``
	value.
	"""

	def syncContentPackages(params=None):
		"""
		Do whatever is necessary to sync content packages.

		If this is done, and the sync results in a change, this
		should fire an :class:`IContentPackageLibrarySynchedEvent`.
		By the time this event is fired, any added/removed/modified
		events for individual content packages will have been fired.

		:param params: Synchronization parameters
		:return  Synchronization results
		"""

class IContentPackageLibraryWillSyncEvent(IObjectEvent):
	"""
	Fired when a content package library has been asked to sync,
	before it does so.

	If the sync process results in changes, the :class:`IContentPackageLibraryModifiedOnSyncEvent`
	will be fired.

	Finally, whether or not there were changes, if the synchronization
	completed, the class:`IContentPackageLibraryDidSyncEvent`
	will be fired.

	.. warning:: Because the ``contentPackages`` property may be in the process
		of mutating, and in general this library may not be stable,
		you should avoid accessing any content-package related
		information about this library in an event listener.
	"""

	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

@interface.implementer(IContentPackageLibraryWillSyncEvent)
class ContentPackageLibraryWillSyncEvent(ObjectEvent):

	def __init__(self, obj, params=None):
		super(ContentPackageLibraryWillSyncEvent, self).__init__(obj)
		self.params = params

class IContentPackageLibraryDidSyncEvent(IObjectEvent):
	"""
	A library completed synchronization, with or without changes.
	"""

	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

	results = Object(ISynchronizationResults,
					 title="Synchronization results",
					 required=False)

@interface.implementer(IContentPackageLibraryDidSyncEvent)
class ContentPackageLibraryDidSyncEvent(ObjectEvent):

	def __init__(self, obj, params=None, results=None):
		super(ContentPackageLibraryDidSyncEvent, self).__init__(obj)
		self.params = params
		self.results = results

class IContentPackageLibraryModifiedOnSyncEvent(IObjectModifiedEvent):
	"""
	An event fired when a content package library has completed
	a synchronization that resulted in changes. This is fired
	after events for individual content package changes.
	"""
	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

	results = Object(ISynchronizationResults,
					 title="Synchronization results",
					 required=False)
	# JAM: Should this be a plain ObjectEvent, not
	# ObjectModifiedEvent (that way none of the indexing logic or
	# similar gets invoked)? But the `attributes` property
	# of ModifiedEvent might be useful

@interface.implementer(IContentPackageLibraryModifiedOnSyncEvent)
class ContentPackageLibraryModifiedOnSyncEvent(ObjectModifiedEvent):
	"""
	Content package library synced event.
	"""

	def __init__(self, obj, params=None, results=None, *descriptions):
		super(ContentPackageLibraryModifiedOnSyncEvent, self).__init__(obj, *descriptions)
		self.params = params
		self.results = results

class IAllContentPackageLibrariesWillSyncEvent(interface.Interface):
	"""
	An event fired before all ContentPackage Libraries are synced
	"""

	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

@interface.implementer(IAllContentPackageLibrariesWillSyncEvent)
class AllContentPackageLibrariesWillSyncEvent(object):
	"""
	Before all Content package libraries are synced event.
	"""

	def __init__(self, params=None):
		self.params = params

class IAllContentPackageLibrariesDidSyncEvent(interface.Interface):
	"""
	An event fired when all ContentPackage Libraries have been synced
	"""

	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

	results = Object(ISynchronizationResults,
					 title="Synchronization results",
					 required=False)

@interface.implementer(IAllContentPackageLibrariesDidSyncEvent)
class AllContentPackageLibrariesDidSyncEvent(object):
	"""
	All Content package libraries synced event.
	"""

	def __init__(self, params=None, results=None):
		self.params = params
		self.results = results

class IContentPackageAddedEvent(IObjectAddedEvent):
	"""
	An event fired when a content package has been added
	"""
	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

@interface.implementer(IContentPackageAddedEvent)
class ContentPackageAddedEvent(ObjectAddedEvent):

	def __init__(self, obj, params=None, results=None):
		super(ContentPackageAddedEvent, self).__init__(obj)
		self.params = params
		self.results = results

class IContentPackageRemovedEvent(IObjectRemovedEvent):
	"""
	An event fired when a content package has been removed.
	"""
	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

@interface.implementer(IContentPackageRemovedEvent)
class ContentPackageRemovedEvent(ObjectRemovedEvent):

	def __init__(self, obj, params=None, results=None):
		super(ContentPackageRemovedEvent, self).__init__(obj)
		self.params = params
		self.results = results

class IGlobalContentPackageLibrary(ISyncableContentPackageLibrary):
	"""
	A non-persistent content library that needs to be synchronized
	on every startup.
	"""

class IPersistentContentPackageLibrary(IPersistent,
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
								   "from this named platform.",
								   required=False)
	Version = Int(title="The version of the layout of resources",
				  default=1, min=1)

	root = Object(IDelimitedHierarchyBucket,
				 title="The key designating this entry in the hierarchy.",
				 default=None)
	root.setTaggedValue('_ext_excluded_out', True)


	# XXX: Fill in missing to match disk layout. Should we have pointers
	# to children?

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
		object having the given `sibling_name`. There is no guarantee whether such
		a sibling key actually exists.

		If the sibling_name has multiple levels, then the returned key
		may be a key nested beneath new intermediate buckets.

		If the sibling_name has a fragment identifier or is URL
		encoded, the results are undefined and may vary from
		implementation to implementation. In particular, different
		sibling_names (because of fragment identifiers) may result in
		the same returned key. Therefore, it is a best practice for the *caller*, who
		presumably knows something about the domain the name is coming from,
		to perform any URL-like manipulation.
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
	will be the :class:`IContentPackageLibrary`. The ``__name__```` is fixed to be the ntiid.
	"""
	ordinal = Int(title="The number (starting at 1) representing which nth child of the parent I am.",
				  default=1, min=1)
	href = TextLine(title="A relative path within the containing bucket",
					description="This may include URL fragments when the same key is re-used",
					default='')
	key = Object(IDelimitedHierarchyKey,
				 title="Key that identifies where the contents for this unit are",
				 description="Should have a bucket its relative to; will not have fragment"
				 	" identifiers, and thus may be reused within a hierarchy",
				 default=None)
	ntiid = ValidNTIID(title="The NTIID for this item",
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
											  value_type=ValidNTIID(title="The embedded NTIID"),
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
								 default=-1)
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

class IContentPackageUnmodifiedEvent(IObjectEvent):
	"""
	A special type of event to signal a content package
	was not modififed
	"""

	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

	results = Object(ISynchronizationResults,
					 title="Synchronization results",
					 required=False)

@interface.implementer(IContentPackageUnmodifiedEvent)
class ContentPackageUnmodifiedEvent(ObjectEvent):
	pacakge = alias('object')

	def __init__(self, obj, params=None, results=None):
		ObjectEvent.__init__(self, obj)
		self.params = params
		self.results = results

class IContentPackageReplacedEvent(IObjectModifiedEvent):
	"""
	A special type of modification event sent when a content package
	is replaced in the library by an update.

	Unlike most normal containers, a content package library is not
	guaranteed to maintain identity when objects change. This event
	can and should be used to determine when a content package is being
	replaced; you have access to both the old and incoming object. If
	you have data stored directly on the content package object, you should
	take appropriate steps to copy/move/update that data on the new object.

	Note particularly that the children might be different between the two
	objects.
	"""

	replacement = Object(IContentPackage,
						 title="The replacement object; same as .object")

	original = Object(IContentPackage,
					  title="The object being replaced")

	params = Object(ISynchronizationParams,
					title="Synchronization parameters",
					required=False)

	results = Object(ISynchronizationResults,
					 title="Synchronization results",
					 required=False)

@interface.implementer(IContentPackageReplacedEvent)
class ContentPackageReplacedEvent(ObjectModifiedEvent):

	original = None
	replacement = alias('object')

	def __init__(self, replacement, original, params=None, results=None, *descriptions):
		ObjectModifiedEvent.__init__(self, replacement, *descriptions)
		self.original = original
		self.params = params
		self.results = results

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

class IPersistentFilesystemContentPackageLibrary(IPersistentContentPackageLibrary,
												 IFilesystemContentPackageLibrary):
	pass

class IGlobalContentPackage(interface.Interface):
	"""
	A marker interface for a package in the global library
	"""

class IGlobalFilesystemContentPackageLibrary(IGlobalContentPackageLibrary,
											 IFilesystemContentPackageLibrary):
	pass

# Content bundles

class IContentPackageBundle(IDisplayableContent,
							ILastModified,
							IShouldHaveTraversablePath,
							dub_interfaces.IDCTimes,
							IAnnotatable):
	"""
	A (typically persistent) object representing a collection
	of one or more content packages, presented as a viewable unit
	in the user interface. These bundles may have additional
	resources associated with them and may imply certain types
	of security precautions or other.

	When arranged into a hierarchy, the parent for this item
	should be a class:`IContentPackageBundleLibrary`, and its
	``__name__`` should be a synonym for its NTIID.
	"""

	# However, there are other places that can refer to a bundle,
	# so we don't *force* them to be inside a library
	# containers(str('.IContentPackageBundleLibrary'))
	# __parent__.required = False


	root = Object(IDelimitedHierarchyItem,
				  title="The key giving the root of this content package",
				  description="Will be externalized through the href mapper",
				  required=True)
	root.setTaggedValue('_ext_excluded_out', True)

	ntiid = ValidNTIID(title="The NTIID for this item",
					 default=None,
					 required=False)

	ContentPackages = UniqueIterable(value_type=Object(IContentPackage, title="A content package"),
									 title="The referenced content packages",
									 default=())

class IContentPackageBundleLibrary(IContentContainer):
	"""
	A \"library\" that contains bundles.

	Although specified as a container, note that this is a hierarchy
	of utilities. However, unless otherwise specified in this interface,
	methods are only local to this object.
	"""
	contains(IContentPackageBundle)
	__setitem__.__doc__ = None

	def get(key, default=None):
		"""
		Find the bundle with the given ntiid in this library
		or a parent.
		"""

	def __getitem__(key):
		"""
		Return the bundle with the given ntiid in this library
		or a parent.
		"""

	def getBundles():
		"""
		Return all the bundles from this library
		and the parents.
		"""

class ISyncableContentPackageBundleLibrary(interface.Interface):
	"""
	An abstraction for synchronizing a content bundle library with
	the contents of a :class:`IEnumerableDelimitedHierarchyBucket`.

	Note that the bundle entries should remain persistent and be modified in place,
	if necessary.
	"""

	def syncFromBucket(bundle_bucket):
		"""
		Synchronize the state of the library. The code that calls this should take
		care to use the (abstractly) same bucket every time.

		:param bundle_bucket: The :class:`IEnumerableDelimitedHierarchyBucket`
			to read from. If called with `None`, then the results are undefined;
			in general, calling code should not pass a `None` value, representing a
			missing bucket, as that is likely to be a temporary condition and
			would result in much churn.
		"""

class IContentPackageBundleLibraryModifiedOnSyncEvent(IObjectModifiedEvent):
	"""
	An event fired when a content package bundle library has completed
	a synchronization that resulted in changes. This is fired
	after events for individual content package changes.
	"""

@interface.implementer(IContentPackageBundleLibraryModifiedOnSyncEvent)
class ContentPackageBundleLibraryModifiedOnSyncEvent(ObjectModifiedEvent):
	"""
	Content package bundle synced event.
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
