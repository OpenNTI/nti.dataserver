#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of content bundles.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface
from zope import lifecycleevent

# Because we only expect to store persistent versions
# of these things, and we expect to update them directly
# in place, we make them attribute annotatable.
from zope.annotation.interfaces import IAttributeAnnotatable

from zope.container.contained import Contained

from zope.event import notify

from ZODB.POSException import ConnectionStateError

from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.contentlibrary import DuplicatePacakgeException
from nti.contentlibrary import MissingContentBundleNTIIDException
from nti.contentlibrary import MissingContentPacakgeReferenceException

from nti.contentlibrary.interfaces import IDisplayableContent
from nti.contentlibrary.interfaces import IContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary

from nti.contentlibrary.presentationresource import DisplayableContentMixin

from nti.dublincore.time_mixins import CreatedAndModifiedTimeMixin

from nti.externalization.persistence import NoPickle

from nti.externalization.representation import WithRepr

from nti.property.property import alias

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.wref.interfaces import IWeakRef

from nti.zodb.persistentproperty import PersistentPropertyHolder

@WithRepr
@interface.implementer(IContentPackageBundle, IAttributeAnnotatable)
class ContentPackageBundle(CreatedAndModifiedTimeMixin,
						   DisplayableContentMixin,
						   Contained,
						   SchemaConfigured):

	"""
	Basic implementation of a content package bundle.
	"""
	__external_class_name__ = 'ContentPackageBundle'
	__external_can_create__ = False

	mime_type = mimeType = 'application/vnd.nextthought.contentpackagebundle'

	_SET_CREATED_MODTIME_ON_INIT = False

	# Equality and hashcode not defined on purpose,
	# identity semantics for now!

	# Be careful not to overwrite what we inherit
	createFieldProperties(IDisplayableContent,
						  omit='PlatformPresentationResources')
	createDirectFieldProperties(IContentPackageBundle)

	# the above defined the ntiid property and the name
	# property, but the ntiid property has the constraint on it
	# that we need.
	__name__ = alias('ntiid')

	# IDCExtendedProperties.
	# Note that we're overriding these to provide
	# default values, thus losing the FieldProperty
	# implementation
	creators = ()
	subjects = ()
	contributors = ()
	publisher = ''

	@property
	def PlatformPresentationResources(self):
		"""
		If we do not have a set of presentation assets,
		we echo the first content package we have that does contain
		them. This should simplify things for the clients.
		"""
		ours = super(ContentPackageBundle, self).PlatformPresentationResources
		if ours:
			return ours

		for package in self.ContentPackages:
			theirs = package.PlatformPresentationResources
			if theirs:
				return theirs
		return ()

class PersistentContentPackageBundle(ContentPackageBundle,
									 PersistentPropertyHolder):
	"""
	A persistent implementation of content package bundles.

	As required, references to content packages are
	maintained weakly.
	"""
	# NOTE we don't extend the convenience class PersistentCreatedAndModifiedTimeObject
	# from time_mixins, because it re-introduces the CreatedAndModifiedTimeMixin
	# we got from ContentPackageBundle; that makes it hard to further subclass.

	_ContentPackages_wrefs = ()

	def _set_ContentPackages(self, packages):
		self._ContentPackages_wrefs = tuple([IWeakRef(p) for p in packages])
		if len(self._ContentPackages_wrefs) != len(set(self._ContentPackages_wrefs)):
			raise DuplicatePacakgeException("Duplicate packages")

	def _get_ContentPackages(self):
		result = list()
		for x in self._ContentPackages_wrefs:
			x = x()
			if x is not None:
				result.append(x)
		return result
	ContentPackages = property(_get_ContentPackages, _set_ContentPackages)

	def __repr__(self):
		try:
			return super(PersistentContentPackageBundle, self).__repr__()
		except ConnectionStateError:
			return object.__repr__(self)

	def __str__(self):
		try:
			return super(PersistentContentPackageBundle, self).__str__()
		except ConnectionStateError:
			return object.__str__(self)

	__unicode__ = __str__

_marker = object()

@interface.implementer(IContentPackageBundleLibrary)
class ContentPackageBundleLibrary(CheckingLastModifiedBTreeContainer):
	"""
	BTree-based implementation of a bundle library.
	"""

	__external_can_create__ = False

	def __repr__(self):
		try:
			return "<%s(%s, %s) at %s>" % (self.__class__.__name__,
									   	   self.__name__,
									   	   len(self),
									   	   id(self))
		except ConnectionStateError:
			return object.__repr__(self)

	__str__ = __repr__
	__unicode__ = __str__

	@property
	def _parent_lib(self):
		return component.queryNextUtility(self, IContentPackageBundleLibrary)

	# Only these methods are expected to walk up the utility tree

	def get(self, key, default=None):
		obj = CheckingLastModifiedBTreeContainer.get(self, key, _marker)
		if obj is _marker:
			obj = default
			parent_lib = self._parent_lib
			if parent_lib is not None:
				obj = parent_lib.get(key, default)

		return obj

	def __getitem__(self, key):
		try:
			return CheckingLastModifiedBTreeContainer.__getitem__(self, key)
		except KeyError:
			parent_lib = self._parent_lib
			if parent_lib is None:
				raise

			return parent_lib[key]

	def getBundles(self):
		# recall that lower bundles override higher ones
		seen_ids = set()
		for k, v in self.items():
			seen_ids.add(k)
			yield v

		parent_lib = self._parent_lib
		if parent_lib is None:
			# done
			return

		for bundle in parent_lib.getBundles():
			if bundle.__name__ in seen_ids:
				continue
			seen_ids.add(bundle.__name__)
			yield bundle

#: The name of the file that identifies a directory
#: as a content bundle
_BUNDLE_META_NAME = "bundle_meta_info.json"
BUNDLE_META_NAME = _BUNDLE_META_NAME  # export

from zope.schema.fieldproperty import FieldProperty

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IDelimitedHierarchyKey
from nti.contentlibrary.interfaces import IEnumerableDelimitedHierarchyBucket
from nti.contentlibrary.interfaces import ISyncableContentPackageBundleLibrary
from nti.contentlibrary.interfaces import ContentPackageBundleLibraryModifiedOnSyncEvent

from nti.contentlibrary.wref import contentunit_wref_to_missing_ntiid

from nti.ntiids.schema import ValidNTIID

from nti.schema.field import IndexedIterable

class IContentBundleMetaInfo(IContentPackageBundle):

	ContentPackages = IndexedIterable(title="An iterable of NTIIDs of sub-containers embedded via reference in this content",
									  value_type=ValidNTIID(title="The embedded NTIID"),
									  unique=True,
									  default=())
_IContentBundleMetaInfo = IContentBundleMetaInfo # alias

@EqHash('ntiid')
@NoPickle
@WithRepr
class ContentBundleMetaInfo(object):
	"""
	Meta-information.

	Instead of creating fields and a schema, we will simply read
	in anything found in the json and store them in ourself.

	Validation and updating is delayed until a full adapting schema call
	can be used. The only exception is for the NTIIDs that make up
	content package references.
	"""

	ContentPackages = FieldProperty(IContentBundleMetaInfo['ContentPackages'])

	_ContentPackages_wrefs = ()

	def __init__(self, key_or_source, content_library, require_ntiid=True):
		# For big/complex JSON, we want to avoid loading the JSON
		# and turning it indo objects unless the timestamp is newer;
		# however, here we need the NTIID, which comes out of the file;
		# also we expect it to be quite small
		if IDelimitedHierarchyKey.providedBy(key_or_source):
			json_value = key_or_source.readContentsAsJson()
		else:
			json_value = key_or_source

		# TODO: If there is no NTIID, we should derive one automatically
		# from the key name
		if require_ntiid and 'ntiid' not in json_value:
			raise MissingContentBundleNTIIDException("Missing ntiid", key_or_source)

		for k, v in json_value.items():
			setattr(self, str(k), v)

		if IDelimitedHierarchyKey.providedBy(key_or_source):
			self.key = key_or_source
			self.createdTime = key_or_source.createdTime
			self.lastModified = key_or_source.lastModified
		else:
			self.key = None
			self.createdTime = self.lastModified = time.time()

		if self.ContentPackages:
			self._ContentPackages_wrefs = self.getContentPackagesWrefs(content_library)
			self.__dict__[str('ContentPackages')] = self._ContentPackages_wrefs

	def getContentPackagesWrefs(self, library):
		"""
		persistent content bundles want to refer to weak refs;
		we read the meta as ntiid strings that we either resolve
		to actual packages (which we then weak ref, so that equality works out),
		or weak refs to missing ntiids
		"""
		cps = []
		for ntiid in self.ContentPackages:
			cp = library.get(ntiid)
			if cp:
				cps.append(IWeakRef(cp))
			else:
				cps.append(contentunit_wref_to_missing_ntiid(ntiid))

		return tuple(cps)
_ContentBundleMetaInfo = ContentBundleMetaInfo # alias

from nti.contentlibrary.dublincore import DCMETA_FILENAME
from nti.contentlibrary.dublincore import read_dublincore_from_named_key

from nti.externalization.internalization import validate_named_field_value

from nti.zodb import readCurrent as _readCurrent

def _validate_package_refs(bundle, meta):
	try:
		if 		len(bundle._ContentPackages_wrefs) == len(meta._ContentPackages_wrefs) \
			and len([x for x in meta._ContentPackages_wrefs if x() is not None]) == 0:
			# Wrefs are the same size, but nothing is resolvable (e.g. not in the library).
			raise MissingContentPacakgeReferenceException(
					'A package reference no longer exists in the library. Content issue? (refs=%s)' %
					[getattr(x, '_ntiid', None) for x in meta._ContentPackages_wrefs])
	except AttributeError:
		# Not sure we can do anything here.
		pass

def synchronize_bundle(data_source, bundle,
					   content_library=None,
					   excluded_keys=(),
					   _meta=None,
					   update_bundle=True):
	"""
	Given either a :class:`IDelimitedHierarchyKey` whose contents are a JSON
	or a JSON source, and an object representing a :class:`IContentPackageBundle`, synchronize
	the bundle fields (those declared in the interface) to match
	the JSON values.

	This is different from normal externalization/internalization in that
	it takes care not to set any fields whose values haven't changed.

	The bundle object will have its bundle-standard `root` property
	set to the ``data_source`` bucket.

	:keyword content_library: The implementation of :class:`IContentPackageLibrary`
		that should be used to produce the ContentPackage objects. These will be
		stored in the bundle as weak references, possibly to missing NTIIDs.
		The bundle implementation should either extend :class`PersistentContentPackageBundle`
		or provide its own setter implementation that deals with this.

		If you do not provide this utility, the currently active library will
		be used.
	"""
	# we can't check the lastModified dates, the bundle object
	# might have been modified independently
	if content_library is None:
		content_library = component.getUtility(IContentPackageLibrary)

	bundle_iface = IContentPackageBundle
	# ^ In the past, we used interface.providedBy(bundle), but that
	# could let anything be set
	meta = _meta or _ContentBundleMetaInfo(data_source, content_library,
										   require_ntiid='ntiid' not in excluded_keys)
	fields_to_update = (set(meta.__dict__)
						- set(excluded_keys)
						- {'lastModified', 'createdTime', 'modified', 'created'})

	# Be careful to only update fields that have changed
	modified = False
	for k in fields_to_update:
		if not bundle_iface.get(k):
			# not an interface field, ignore
			continue

		if k == 'ContentPackages':
			# Treat these specially so that we don't have to resolve
			# weak references; if everything was *missing*, the ContentPackages
			# could come back as empty both places
			try:
				needs_copy = bundle._ContentPackages_wrefs != meta._ContentPackages_wrefs
			except AttributeError:
				needs_copy = getattr(bundle, k, None) != getattr(meta, k)
			if needs_copy:
				# Our ContentPackages actually may bypass the interface by already
				# being weakly referenced if missing, hence avoiding
				# the validation step
				modified = True
				bundle.ContentPackages = meta.ContentPackages

			# We may not have had changes to our wrefs, but we should still validate
			# that something weird did not occur with our packages.
			_validate_package_refs(bundle, meta)
		elif getattr(bundle, k, None) != getattr(meta, k):
			modified = True
			validate_named_field_value(bundle, bundle_iface, str(k), getattr(meta, k))()

	if update_bundle and bundle.root != meta.key.__parent__:
		modified = True
		bundle.root = meta.key.__parent__

	if modified:
		bundle.updateLastMod(meta.lastModified)
	elif bundle.lastModified < meta.lastModified:
		bundle.updateLastModIfGreater(meta.lastModified)

	return modified

def sync_bundle_from_json_key(data_key, bundle, content_library=None,
							  dc_meta_name=DCMETA_FILENAME,
							  excluded_keys=(),
							  _meta=None,
							  dc_bucket=None,
							  update_bundle=True):
	"""
	:keyword dc_meta_name: If given (defaults to a standard value),
		DublinCore metadata will be read from this file (a sibling of the `data_key`).
		You can use a non-standard
		filename if you might have multiple things in the same bucket.
	"""
	result = synchronize_bundle(data_key, bundle,
								content_library=content_library,
								excluded_keys=excluded_keys,
								_meta=_meta,
								update_bundle=update_bundle)
	# Metadata if we need it
	dc_bucket = data_key.__parent__ if dc_bucket is None else dc_bucket
	read_dublincore_from_named_key(bundle, dc_bucket, dc_meta_name)

	return result

@interface.implementer(ISyncableContentPackageBundleLibrary)
@component.adapter(IContentPackageBundleLibrary)
class _ContentPackageBundleLibrarySynchronizer(object):

	def __init__(self, context):
		self.context = context

	def syncFromBucket(self, bucket):
		content_library = component.getSiteManager(self.context).getUtility(IContentPackageLibrary)
		_readCurrent(content_library)
		_readCurrent(self.context)

		bundle_meta_keys = list()

		for child in bucket.enumerateChildren():
			if not IEnumerableDelimitedHierarchyBucket.providedBy(child):
				# not a directory
				continue
			bundle_meta_key = child.getChildNamed(_BUNDLE_META_NAME)
			if not IDelimitedHierarchyKey.providedBy(bundle_meta_key):
				# Not a readable file
				continue

			bundle_meta_keys.append(bundle_meta_key)

		need_event = False

		# Trivial case: everything is gone
		# TODO: How do we want to handle deletions?
		# Ideally we want to "archive" the objects somewhere probably
		# (a special 'archive' subcontainer?)
		if not bundle_meta_keys and self.context:
			logger.info("Removing all bundles from library %s: %s", self.context, list(self.context))
			need_event = True
			for k in list(self.context):
				del self.context[k]  # fires bunches of events
		else:
			bundle_metas = {_ContentBundleMetaInfo(k, content_library) for k in bundle_meta_keys}
			all_ntiids = {x.ntiid for x in bundle_metas}
			# Now determine what to add/update/remove.
			# Order matters here, very much.
			# The __contains__ operation for keys does not take parent
			# libraries into account, nor does iterating the keys; thus,
			# we're safe by checking the ntiids against our context.
			# By the time we look for things to update, we know we will
			# be accessing an item local in our context, not from parent,
			# even though __getitem__ is recursive.

			things_to_add = {x for x in bundle_metas if x.ntiid not in self.context}
			# Take those out
			bundle_metas = bundle_metas - things_to_add

			things_to_update = {x for x in bundle_metas
								if x.lastModified > self.context[x.ntiid].lastModified}

			# All of these remaining things haven't changed,
			# but by definition must still be in the container
			bundle_metas = bundle_metas - things_to_update

			# any ntiids in the container that we don't have on disk
			# have to go
			del_ntiids = {x for x in self.context if x not in all_ntiids}

			def _update_bundle(bundle, meta):
				sync_bundle_from_json_key(meta.key, bundle,
										  content_library=content_library,
										  # pass in the existing object as an optimization
										  _meta=meta)
				assert meta.ntiid == bundle.ntiid

			# Start with the adds
			if things_to_add:
				need_event = True
				logger.info("Adding bundles to library %s: %s",
							self.context, things_to_add)
				for meta in things_to_add:
					bundle = PersistentContentPackageBundle()
					bundle.createdTime = meta.createdTime
					_update_bundle(bundle, meta)

					lifecycleevent.created(bundle)
					self.context[meta.ntiid] = bundle  # added

			# Now the deletions
			if del_ntiids:
				logger.info("Removing bundles from library %s: %s",
							self.context, del_ntiids)
				for ntiid in del_ntiids:
					need_event = True
					del self.context[ntiid]

			# Now any updates
			if things_to_update:
				need_event = True
				logger.info("Updating bundles in library %s: %s",
							self.context, things_to_update)
				for meta in things_to_update:
					bundle = self.context[meta.ntiid]
					_update_bundle(bundle, meta)
					# TODO: make update_bundle return the changed attributes?
					lifecycleevent.modified(bundle)

		if need_event:
			event = ContentPackageBundleLibraryModifiedOnSyncEvent(self.context)
			event.bucket = bucket
			notify(event)
		else:
			logger.info("Nothing to do to sync library %s", self.context)
