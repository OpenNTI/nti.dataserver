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
import urllib

from zope import interface
from zope import component

import repoze.lru

from nti.utils.property import readproperty

from . import eclipse
from . import library

from .contentunit import ContentUnit
from .contentunit import ContentPackage
from .interfaces import IFilesystemContentUnit
from .interfaces import IFilesystemContentPackage
from .interfaces import IFilesystemContentPackageLibrary
from .interfaces import IFilesystemKey
from .interfaces import IFilesystemBucket
from .interfaces import IGlobalFilesystemContentPackageLibrary
from .interfaces import IPersistentFilesystemContentUnit
from .interfaces import IPersistentFilesystemContentPackage
from .interfaces import IPersistentFilesystemContentPackageLibrary

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

from .bucket import AbstractBucket
from .bucket import AbstractKey

class _AbsolutePathMixin(object):

	@readproperty
	def absolute_path(self):
		pabspath = getattr(self.__parent__, 'absolute_path', None)
		if pabspath and self.__name__:
			return os.path.join(pabspath,
								self.__name__)
		raise ValueError("Not yet", self.__parent__, pabspath, self.__name__)


@interface.implementer(IFilesystemKey)
class FilesystemKey(AbstractKey, _AbsolutePathMixin):
	pass


@interface.implementer(IFilesystemBucket)
class FilesystemBucket(AbstractBucket, _AbsolutePathMixin):

	_key_type = FilesystemKey

	def enumerateChildren(self):
		absolute_path = self.absolute_path
		if not os.path.isdir(absolute_path):
			return

		for k in os.listdir(absolute_path):
			if k.startswith('.'):
				continue

			absk = os.path.join(absolute_path, k)
			if isinstance(absk, bytes):
				k = k.decode('utf-8')
				absk = absk.decode('utf-8')
			if os.path.isdir(absk):
				yield type(self)(self, k)
			else:
				yield self._key_type(self, k)

from nti.dublincore.interfaces import ILastModified

@interface.implementer(ILastModified)
class _FilesystemLibraryEnumeration(library.AbstractContentPackageEnumeration):
	"""
	A library enumeration that will examine the root to find possible content packages.

	If the library directory does not exist, there will be no content packages,
	and the modification times will be negative, but nothing will throw errors.
	This makes it safe to use speculatively.
	"""

	_bucket_factory = FilesystemBucket

	def __init__(self, root, package_factory=None, unit_factory=None):
		self._root = root
		self.__package_factory = package_factory or FilesystemContentPackage
		self._unit_factory = unit_factory or FilesystemContentUnit

	@property
	def root(self):
		"""The root directory path we will examine."""
		return os.path.abspath(self._root)

	@property
	def absolute_path(self):
		# Cooperate with the buckets and keys to get
		# an absolute path on disk.
		return self.root

	@property
	def name(self):
		# For BWC with the old Bucket/Key system that used
		# a full path as name
		return self.absolute_path

	def _time(self, key):
		try:
			return os.stat(self._root)[key]
		except OSError:
			return -1

	@property
	def createdTime(self):
		return self._time(os.path.stat.ST_CTIME)

	@property
	def lastModified(self):
		return self._time(os.path.stat.ST_MTIME)

	def _package_factory(self, bucket):
		return _package_factory(bucket, self.__package_factory, self._unit_factory)

	def _possible_content_packages(self):
		if not os.path.isdir(self._root):
			return

		for p in os.listdir(self._root):
			absp = os.path.join(self._root, p)
			absp = os.path.abspath(absp)
			if os.path.isdir(absp) and _hasTOC(absp):
				p = p.decode('utf-8') if isinstance(p, bytes) else p
				yield self._bucket_factory(bucket=self, name=p)


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

@interface.implementer(IGlobalFilesystemContentPackageLibrary)
class GlobalFilesystemContentPackageLibrary(library.GlobalContentPackageLibrary,
											AbstractFilesystemLibrary):
	pass

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

from .contentunit import _exist_cache
from .contentunit import _content_cache

from nti.dublincore.time_mixins import TimeProperty
class _FilesystemTime(object):
	"""
	A descriptor that caches a filesystem time, allowing
	for errors in case its accessed too early.
	"""
	def __init__( self, name, st ):
		self._st = st
		self._name = str(name)

	def __get__(self, inst, klass):
		if inst is None:
			return self

		if self._name in inst.__dict__:
			return inst.__dict__[self._name]

		try:
			val = os.stat(inst.filename)[self._st]
		except (OSError,TypeError):
			return 0
		else:
			inst.__dict__[self._name] = val
			return val

	def __set__(self, inst, val):
		pass

@interface.implementer(IFilesystemContentUnit)
class FilesystemContentUnit(ContentUnit):
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


	def _get_filename(self):
		return self.key.absolute_path if self.key else None
	filename = property(_get_filename, lambda x, y: None)

	@property
	def dirname(self):
		filename = self.filename
		if filename:
			return os.path.dirname(filename)


	lastModified = _FilesystemTime('lastModified', os.path.stat.ST_MTIME)
	modified = TimeProperty('lastModified', writable=False, cached=True)


	createdTime = _FilesystemTime('createdTime', os.path.stat.ST_CTIME)
	created = TimeProperty('createdTime', writable=False, cached=True)

	@repoze.lru.lru_cache(None, cache=_content_cache)
	def read_contents(self):
		try:
			with open(self.filename, 'r') as f:
				return f.read()
		except IOError:
			return None

	def get_parent_key(self):
		return self.key.bucket

	def make_sibling_key(self, sibling_name):
		__traceback_info__ = self.filename, sibling_name
		assert bool(sibling_name)
		assert not sibling_name.startswith('/')

		# If we get a multi-segment path, we need to deconstruct it
		# into bucket parts to be sure that it externalizes
		# correctly.
		# Just in case they send url-encoded things, decode them
		parts = [urllib.unquote(x) for x in sibling_name.split('/')]
		parts = [x.decode('utf-8') if isinstance(x, bytes) else x for x in parts]
		parent = self.key.bucket
		for part in parts[:-1]:
			parent = type(self.key.bucket)(bucket=parent, name=part)

		key = type(self.key)(bucket=parent, name=parts[-1])

		assert key.absolute_path == os.path.join(os.path.dirname(self.filename), *parts)

		return key

	@repoze.lru.lru_cache(None, cache=_content_cache)  # first arg is ignored. This caches with the key (self, sibling_name)
	def _do_read_contents_of_sibling_entry(self, sibling_name):
		try:
			with open(self.make_sibling_key(sibling_name).absolute_path, 'r') as f:
				return f.read()
		except (OSError, IOError):
			return None

	def read_contents_of_sibling_entry(self, sibling_name):
		if self.filename:
			return self._do_read_contents_of_sibling_entry(sibling_name)

	@repoze.lru.lru_cache(None, cache=_exist_cache)
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

	def __hash__(self):
		return hash(self.filename)

@interface.implementer(IFilesystemContentPackage)
class FilesystemContentPackage(ContentPackage, FilesystemContentUnit):
	"""
	Adds the `filename` property to the ContentPackage.
	"""

	TRANSIENT_EXCEPTIONS = (IOError,)


from persistent import Persistent

@interface.implementer(IPersistentFilesystemContentUnit)
class PersistentFilesystemContentUnit(Persistent,
									  FilesystemContentUnit):
	"""
	A persistent version of a content unit.
	"""

@interface.implementer(IPersistentFilesystemContentPackage)
class PersistentFilesystemContentPackage(Persistent,
										 FilesystemContentPackage):
	"""
	A persistent content package.
	"""

class _PersistentFilesystemLibraryEnumeration(Persistent,
											  _FilesystemLibraryEnumeration):

	def __init__(self, root):
		Persistent.__init__(self)
		_FilesystemLibraryEnumeration.__init__(self,
											   root,
											   PersistentFilesystemContentPackage,
											   PersistentFilesystemContentUnit)


@interface.implementer(IPersistentFilesystemContentPackageLibrary)
class PersistentFilesystemLibrary(AbstractFilesystemLibrary,
								  library.PersistentContentPackageLibrary):

	@classmethod
	def _create_enumeration(cls, root):
		return _PersistentFilesystemLibraryEnumeration(root)

from .interfaces import ISiteLibraryFactory
from nti.externalization.persistence import NoPickle

@component.adapter(IGlobalFilesystemContentPackageLibrary)
@interface.implementer(ISiteLibraryFactory)
@NoPickle
class GlobalFilesystemSiteLibraryFactory(object):

	def __init__(self, context):
		self.context = context

	def library_for_site_named(self, name):
		enumeration = self.context._enumeration
		root = enumeration.root

		site_dir = os.path.join( root, 'sites', name )

		# whether or not it exists we return it so that
		# it can be registered for the future.
		return PersistentFilesystemLibrary(site_dir)
