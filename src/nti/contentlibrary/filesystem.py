#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objects for creating IContentLibrary objects based on the filesystem.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
from os.path import join as path_join

from zope import component
from zope import interface

from zope.cachedescriptors.method import cachedIn

from ZODB.POSException import ConnectionStateError

from nti.property.property import readproperty
from nti.property.property import CachedProperty

from .contentunit import ContentUnit
from .contentunit import ContentPackage

from .interfaces import IFilesystemKey
from .interfaces import IFilesystemBucket
from .interfaces import IContentPackageLibrary
from .interfaces import IFilesystemContentUnit
from .interfaces import IFilesystemContentPackage
from .interfaces import IGlobalContentPackageLibrary
from .interfaces import IFilesystemContentPackageLibrary
from .interfaces import IEnumerableDelimitedHierarchyBucket
from .interfaces import IPersistentFilesystemContentUnit
from .interfaces import IPersistentFilesystemContentPackage
from .interfaces import IGlobalFilesystemContentPackageLibrary
from .interfaces import IPersistentFilesystemContentPackageLibrary
from .interfaces import IDelimitedHierarchyContentPackageEnumeration

from . import eclipse
from . import library

def _TOCPath(path):
	return os.path.abspath(path_join(path, eclipse.TOC_FILENAME))

def _hasTOC(path):
	""" Does the given path point to a directory containing a TOC file?"""
	return os.path.exists(_TOCPath(path))

def _isTOC(path):
	return os.path.basename(path) == eclipse.TOC_FILENAME

def _package_factory(bucket, _package_factory=None, _unit_factory=None):
	"""
	Given a FilesystemBucket, return a package if it is sutable.
	"""

	directory = bucket.absolute_path

	if not _hasTOC(directory):
		return None

	_package_factory = _package_factory or FilesystemContentPackage
	_unit_factory = _unit_factory or FilesystemContentUnit

	key = FilesystemKey(bucket=bucket, name=eclipse.TOC_FILENAME)

	temp_entry = FilesystemContentUnit(key=key)
	assert key.absolute_path == _TOCPath(directory) == temp_entry.filename

	package = eclipse.EclipseContentPackage(temp_entry, _package_factory, _unit_factory)

	__traceback_info__ = directory, bucket, key, temp_entry, package
	assert package.key.bucket == bucket
	assert package is not temp_entry

	return package

class _FilesystemTime(object):
	"""
	A descriptor that optionally caches a filesystem time, allowing
	for errors in case it is accessed too early.
	"""

	default_time = -1
	cache = True

	def __init__( self, name, st,
				  attr_name='filename',
				  default_time=None,
				  cache=True ):
		self._st = st
		self._name = str(name)
		self._attr_name = str(attr_name)
		if default_time is not None:
			self.default_time = default_time
		if not cache:
			self.cache = cache

	def __get__(self, inst, klass):
		if inst is None:
			return self

		if self.cache and self._name in inst.__dict__:
			return inst.__dict__[self._name]

		try:
			val = os.stat(getattr(inst, self._attr_name))[self._st]
		except (OSError,TypeError):
			return self.default_time
		else:
			if 		self._name not in inst.__dict__ \
				or 	inst.__dict__[self._name] != val:
				# Store only if we've changed.
				inst.__dict__[self._name] = val
				if hasattr(inst, '_p_changed'):
					inst._p_changed = True
			return val

	def __set__(self, inst, val):
		# Should we allow set?
		pass

from .bucket import AbstractKey
from .bucket import AbstractBucket

from zope.dublincore.interfaces import IDCTimes

from nti.coremetadata.interfaces import ILastModified

from nti.dublincore.time_mixins import TimeProperty

class _AbsolutePathMixin(object):

	@readproperty
	def absolute_path(self):
		pabspath = getattr(self.__parent__, 'absolute_path', None)
		if pabspath and self.__name__:
			return os.path.join(pabspath,
								self.__name__)
		raise ValueError("Not yet", self.__parent__, pabspath, self.__name__)

@interface.implementer(IDCTimes)
class _FilesystemTimesMixin(object):

	lastModified = _FilesystemTime('lastModified', os.path.stat.ST_MTIME, 'absolute_path',
								   cache=False)
	createdTime = _FilesystemTime('createdTime', os.path.stat.ST_CTIME, 'absolute_path')

	# Here we cache the datetime object based on the timestamp
	modified = TimeProperty('lastModified', writable=False, cached=True)
	created = TimeProperty('createdTime', writable=False, cached=True)

from lxml import etree
etree_parse = getattr(etree, 'parse')

from nti.schema.eqhash import EqHash

@interface.implementer(IFilesystemKey,
					   ILastModified)
@EqHash('absolute_path')
class FilesystemKey(AbstractKey,
					_AbsolutePathMixin,
					_FilesystemTimesMixin):

	@CachedProperty('absolute_path', 'lastModified')
	def _contents(self):
		try:
			with open(self.absolute_path, 'rb') as f:
				return f.read()
		except IOError:
			return None

	def readContents(self):
		return self._contents

	@cachedIn('_v_readContentsAsText')
	def _do_readContentsAsText(self, contents, encoding):
		if contents is not None:
			return contents.decode(encoding)

	def readContentsAsText(self, encoding="utf-8"):
		return self._do_readContentsAsText(self._contents, encoding)

	def readContentsAsETree(self):
		# TODO: Pass the base_url?
		root = etree_parse( self.absolute_path ).getroot()
		return root

	def readContentsAsYaml(self):
		# simplejson.loads does a .read() to get the full
		# contents in one go anyway, so we're better off
		# just using our cached contents. However, yaml actually
		# offers the possibility of using a streaming parser
		with open(self.absolute_path, 'rb') as f:
			return self._do_readContentsAsYaml(f)

@interface.implementer(IFilesystemBucket)
class FilesystemBucket(AbstractBucket,
					   _AbsolutePathMixin,
					   _FilesystemTimesMixin):

	_key_type = FilesystemKey

	@CachedProperty
	def _children_cache(self):
		"""
		Because there is caching done by keys/buckets of contents and
		modification time, it is useful to return the same instances
		every time.
		"""
		return {}

	def enumerateChildren(self):
		absolute_path = self.absolute_path
		if not os.path.isdir(absolute_path):
			return

		# note that we don't handle an entry going from
		# being a key to a bucket or vice versa;
		# we also don't handle cleaning up deleted keys/buckets,
		# they just leak memory
		cache = self._children_cache

		for k in os.listdir(absolute_path):
			if k.startswith('.'):
				continue

			if k not in cache:
				absk = os.path.join(absolute_path, k)
				if isinstance(absk, bytes):
					k = k.decode('utf-8')
					absk = absk.decode('utf-8')

				if os.path.isdir(absk):
					cache[k] = type(self)(self, k)
				else:
					cache[k] = self._key_type(self, k)

			yield cache[k]

@interface.implementer(ILastModified)
class _FilesystemLibraryEnumeration(library.AbstractDelimitedHiercharchyContentPackageEnumeration,
									_FilesystemTimesMixin):
	"""
	A library enumeration that will examine the root to find possible content packages.

	If the library directory does not exist, there will be no content packages,
	and the modification times will be negative, but nothing will throw errors.
	This makes it safe to use speculatively.
	"""

	lastSynchronized = 0

	#: Used during persistence and when making absolute paths,
	#: this is the parent enumeration that birthed us.
	parent_enumeration = None

	def __init__(self, root_path, package_factory=None, unit_factory=None):
		if not IEnumerableDelimitedHierarchyBucket.providedBy(root_path):
			root_path = os.path.abspath(root_path)
			if root_path.endswith('/'):
				root_path = root_path[:-1]
			self._root = FilesystemBucket(bucket=self, name=os.path.basename(root_path))
			self._root.absolute_path = root_path
			# Keep this unnamed so it doesn't get in the traversal path
			self._root.__name__ = None
		else:
			self._root = root_path

		self.__package_factory = package_factory or FilesystemContentPackage
		self._unit_factory = unit_factory or FilesystemContentUnit

	_bucket_factory = FilesystemBucket
	_enumeration_factory = None

	def childEnumeration(self, name):
		bucket = self._bucket_factory(bucket=self, name=name)
		enumeration_factory = self._enumeration_factory or type(self)
		result = enumeration_factory(bucket)
		result.parent_enumeration = self
		return result

	@property
	def root(self):
		"""The root bucket we will examine."""
		return self._root

	@property
	def absolute_path(self):
		# Cooperate with the buckets and keys to get
		# an absolute path on disk.
		return self.root.absolute_path

	@property
	def name(self):
		# For BWC with the old Bucket/Key system that used
		# a full path as name
		return self.absolute_path

	def _package_factory(self, bucket):
		return _package_factory(bucket, self.__package_factory, self._unit_factory)

@interface.implementer(IFilesystemContentPackageLibrary)
class AbstractFilesystemLibrary(library.AbstractContentPackageLibrary):
	"""
	A library that will examine the root to find possible content packages
	only the very first time that it is requested to. Changes after that
	point will be ignored. The content packages and parsed
	data will be cached in memory until this library is deleted.

	This library will broadcast :class:`.IObjectCreatedEvent` and
	:class:`.IObjectAddedEvent` for content packages.
	"""

	def __init__(self, root='', **kwargs):
		if 'paths' in kwargs:
			raise TypeError("DynamicFilesystemLibrary does not accept paths, just root")

		root = root or kwargs.pop('root')
		enumeration = self._create_enumeration(root)
		library.AbstractContentPackageLibrary.__init__(self, enumeration, **kwargs)

	@classmethod
	def _create_enumeration(cls, root):
		return _FilesystemLibraryEnumeration(root)

	def __repr__(self):
		try:
			return "<%s(%s)>" % (self.__class__.__name__,
						   		 getattr(self._enumeration, 
										 'absolute_path',
										  self._enumeration.root))
		except ConnectionStateError:
			return object.__repr__(self)

@interface.implementer(IFilesystemContentUnit)
class FilesystemContentUnit(_FilesystemTimesMixin,
							ContentUnit):

	"""
	Adds the `filename` property, an alias of the `key` property
	"""

	def _get_key(self):
		return self.__dict__.get('key', None)
	def _set_key(self, nk):
		if isinstance(nk, basestring):
			raise TypeError("Should provide a real key")
		self.__dict__[str('key')] = nk
	key = property(_get_key, _set_key)

	filename = property(lambda self: self.key.absolute_path if self.key else None)
	absolute_path = filename

	@property
	def dirname(self):
		filename = self.filename
		if filename:
			return os.path.dirname(filename)

	def read_contents(self):
		return self.key.readContents()

	def get_parent_key(self):
		return self.key.bucket

	@cachedIn('_v_make_sibling_keys')
	def make_sibling_key(self, sibling_name):
		# Because keys cache things like dates and contents, it is useful
		# to return the same instance

		__traceback_info__ = self.filename, sibling_name
		assert bool(sibling_name)
		assert not sibling_name.startswith('/')

		# At this point, everything should already be URL-decoded,
		# (and fragments removed) and unicode
		# If we get a multi-segment path, we need to deconstruct it
		# into bucket parts to be sure that it externalizes
		# correctly.
		parts = sibling_name.split('/')
		parent = self.key.bucket
		for part in parts[:-1]:
			parent = type(self.key.bucket)(bucket=parent, name=part)

		key = type(self.key)(bucket=parent, name=parts[-1])

		assert key.absolute_path == os.path.join(os.path.dirname(self.filename), *parts)

		return key

	def _do_read_contents_of_sibling_entry(self, sibling_name):
		return self.make_sibling_key(sibling_name).readContents()

	def read_contents_of_sibling_entry(self, sibling_name):
		if self.filename:
			return self._do_read_contents_of_sibling_entry(sibling_name)

	def does_sibling_entry_exist(self, sibling_name):
		sib_key = self.make_sibling_key(sibling_name)
		return sib_key if os.path.exists(sib_key.absolute_path) else None

	def __repr__(self):
		return "<%s.%s '%s' '%s'>" % (self.__class__.__module__, self.__class__.__name__,
									  self.__name__, self.filename)

	def __eq__(self, other):
		try:
			return self.key == other.key and self.__parent__ == other.__parent__
		except AttributeError:
			return NotImplemented

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		return hash(self.filename)

@interface.implementer(IFilesystemContentPackage)
class FilesystemContentPackage(ContentPackage, FilesystemContentUnit):
	"""
	Adds the `filename` property to the ContentPackage.
	"""

	TRANSIENT_EXCEPTIONS = (IOError,)

	_directory_last_modified = _FilesystemTime('_directory_last_modified',
											   os.path.stat.ST_MTIME,
											   'dirname')
	@property
	def lastModified(self):
		"""
		The modification date of a content package is defined to be
		the most recent of its index file modification time
		and its directory modification time. The ``index.html``
		file found in the ``filename`` is not consulted, because
		this object represents the entire package as a whole.
		"""
		return max( self.index_last_modified, self._directory_last_modified )

# Order matters, we must inherit Persistent FIRST to get the right __getstate__,etc,
# behaviour

from persistent import Persistent

@interface.implementer(IPersistentFilesystemContentUnit)
class PersistentFilesystemContentUnit(Persistent,
									  FilesystemContentUnit):
	"""
	A persistent version of a content unit.
	"""
	
	def __repr__(self):
		try:
			return super(PersistentFilesystemContentUnit, self).__repr__()
		except ConnectionStateError:
			return object.__repr__(self)

@interface.implementer(IPersistentFilesystemContentPackage)
class PersistentFilesystemContentPackage(Persistent,
										 FilesystemContentPackage):
	"""
	A persistent content package.
	"""

	def __repr__(self):
		try:
			return super(PersistentFilesystemContentPackage, self).__repr__()
		except ConnectionStateError:
			return object.__repr__(self)
		
class _PersistentFilesystemLibraryEnumeration(Persistent,
											  _FilesystemLibraryEnumeration):

	def __init__(self, root):
		Persistent.__init__(self)
		_FilesystemLibraryEnumeration.__init__(self,
											   root,
											   PersistentFilesystemContentPackage,
											   PersistentFilesystemContentUnit)
		
	def __repr__(self):
		try:
			return super(_PersistentFilesystemLibraryEnumeration, self).__repr__()
		except ConnectionStateError:
			return object.__repr__(self)

def _GlobalFilesystemLibraryEnumerationUnpickle(parent):
	return getattr(parent, '_enumeration')

class _GlobalFilesystemLibraryEnumeration(_FilesystemLibraryEnumeration):
	"""
	When a global filesystem library enumeration is asked for
	child enumerations, it produces ones that are relative
	to itself, and looked up globally at runtime.
	"""

	_enumeration_factory = _PersistentFilesystemLibraryEnumeration

	def __reduce__(self, *args):
		return _GlobalFilesystemLibraryEnumerationUnpickle, (self.__parent__,)
	__reduce_ex__ = __reduce__

def _GlobalFilesystemUnpickle(library_name):

	name = ''
	if library_name != library.AbstractContentPackageLibrary.__dict__['__name__']:
		name = library_name

	gsm = component.getGlobalSiteManager()
	lib = gsm.queryUtility(IGlobalFilesystemContentPackageLibrary,
						   name=name)
	if lib is None:
		# Hmm, maybe they changed to a different implementation?
		lib = gsm.queryUtility(IGlobalContentPackageLibrary, name=name)

	if lib is None:
		# Hmm, maybe it's not actually registered as global?
		# NOTE: This last one throws!
		lib = gsm.getUtility(IContentPackageLibrary, name=name)

	return lib

@interface.implementer(IGlobalFilesystemContentPackageLibrary)
class GlobalFilesystemContentPackageLibrary(library.GlobalContentPackageLibrary,
											AbstractFilesystemLibrary):
	"""
	When this library is pickled, none of its contents are; instead,
	it is pickled as a lookup to the main global library (if the name
	is not the default name of 'Library', that global library will
	be found instead).
	"""

	@classmethod
	def _create_enumeration(cls, root):
		return _GlobalFilesystemLibraryEnumeration(root)

	def __reduce__(self, *args):
		return _GlobalFilesystemUnpickle, (self.__name__,)
	__reduce_ex__ = __reduce__

# A measure of BWC
EnumerateOnceFilesystemLibrary = GlobalFilesystemContentPackageLibrary
DynamicFilesystemLibrary = EnumerateOnceFilesystemLibrary
StaticFilesystemLibrary = library.EmptyLibrary

def CachedNotifyingStaticFilesystemLibrary(paths=()):
	if not paths:
		return library.EmptyLibrary()

	roots = {os.path.dirname(p) for p in paths}
	if len(roots) == 1:
		return EnumerateOnceFilesystemLibrary(list(roots)[0])
	raise TypeError("Unsupported use of multiple paths")
	# Though we could support it without too much trouble

@interface.implementer(IPersistentFilesystemContentPackageLibrary)
class PersistentFilesystemLibrary(AbstractFilesystemLibrary,
								  library.PersistentContentPackageLibrary):

	@classmethod
	def _create_enumeration(cls, root):
		assert isinstance(root, _PersistentFilesystemLibraryEnumeration)
		return root

	def __repr__(self):
		try:
			return super(PersistentFilesystemLibrary, self).__repr__()
		except ConnectionStateError:
			return object.__repr__(self)
		
from nti.externalization.persistence import NoPickle

from .interfaces import ISiteLibraryFactory

@NoPickle
@component.adapter(IGlobalFilesystemContentPackageLibrary)
@interface.implementer(ISiteLibraryFactory)
class GlobalFilesystemSiteLibraryFactory(object):

	def __init__(self, context):
		self.context = context

	def library_for_site_named(self, name):
		enumeration = IDelimitedHierarchyContentPackageEnumeration(self.context)
		site_enumeration = enumeration.childEnumeration('sites').childEnumeration(name)
		# whether or not it exists we return it so that
		# it can be registered for the future.
		return PersistentFilesystemLibrary(site_enumeration)
