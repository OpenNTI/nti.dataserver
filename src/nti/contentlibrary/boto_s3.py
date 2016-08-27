#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic implementations of IContentUnit functions

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import gzip
import time
import rfc822
import numbers
import datetime
from cStringIO import StringIO

import webob.datetime_utils

from zope import interface

from zope.cachedescriptors.property import Lazy

import repoze.lru

# We mark all of the classes declared here as
# non-pickalable, because we don't have their persistence
# worked out yet.
from nti.externalization.persistence import NoPickle

from nti.property.property import alias

from .interfaces import IS3Key
from .interfaces import IS3Bucket
from .interfaces import IS3ContentUnit
from .interfaces import IS3ContentPackage

from .contentunit import ContentUnit, ContentPackage

from . import eclipse
from . import library

# Make the boto classes fit better with Zope, including making them
# ILocation like and giving them interfaces
import boto.s3.key
import boto.s3.bucket
import boto.exception

interface.classImplements(boto.s3.bucket.Bucket, IS3Bucket)
interface.classImplements(boto.s3.key.Key, IS3Key)
class _WithName:  # NOTE: Not new-style
	__name__ = alias('name')

boto.s3.bucket.Bucket.__bases__ += _WithName,
boto.s3.bucket.Bucket.__parent__ = alias('connection')

boto.s3.key.Key.__bases__ += _WithName,
boto.s3.key.Key.__parent__ = alias('bucket')

class NameEqualityKey(boto.s3.key.Key):
	"""
	A class that tests for equality based on the name and bucket. Two keys with
	the same name in the same bucket will be equal. The same name across
	buckets will not be equal.

	.. caution:: This is only useful with the :class:`NameEqualityBucket`.
		This does not take the connection into account, and
		hence is somewhat dangerous. Only use it if there will be one
		set of credentials in use.
	"""

	# Not taking the connection into account because I don't have time to
	# verify its equality conditions.

	def __eq__(self, other):
		try:
			return self is other or (self.name == other.name and self.bucket == other.bucket)
		except AttributeError:  # pragma: no cover
			return NotImplemented

	def __hash__(self):
		return hash(self.name) + 37 + hash(self.bucket)

class NameEqualityBucket(boto.s3.bucket.Bucket):
	"""
	A class that tests for equality based on the name.

	.. caution:: This does not take the connection into account, and
		hence is somewhat dangerous. Only use it if there will be one
		set of credentials in use.
	"""

	def __init__(self, connection=None, name=None, key_class=NameEqualityKey):
		super(NameEqualityBucket, self).__init__(connection=connection, name=name, key_class=key_class)

	def __eq__(self, other):
		try:
			return self is other or self.name == other.name
		except AttributeError:  # pragma: no cover
			return NotImplemented

	def __hash__(self):
		return hash(self.name) + 37

def key_last_modified(key):
	"""
	Return the last modified value of the key in some form thats actually
	useful, not a goddamn arbitrary format string.

	:return: A float, or None.
	"""
	__traceback_info__ = key, key.last_modified
	if isinstance(key.last_modified, numbers.Number):
		return key.last_modified  # Mainly for tests
	result = rfc822.parsedate_tz(key.last_modified)
	if result is not None:
		result = rfc822.mktime_tz(result)
		# This is supposed to be coming in rfc822 format (see boto.s3.key)
		# But it doesn't always. So try to parse it ourself if we have to
	elif key.last_modified:
		# 2012-05-12T23:15:24.000Z
		result = datetime.datetime.strptime(key.last_modified, '%Y-%m-%dT%H:%M:%S.%fZ')
		result = result.replace(tzinfo=webob.datetime_utils.UTC)
		result = time.mktime(result.timetuple())
	return result

from .contentunit import _exist_cache
from .contentunit import _content_cache

@repoze.lru.lru_cache(None, cache=_content_cache)  # first arg is ignored. This caches with the key (key,)
def _read_key(key):
	data = None
	if key:
		data = key.get_contents_as_string()
		if key.content_encoding == 'gzip':
			stream = StringIO(data)
			gzip_stream = gzip.GzipFile(fileobj=stream, mode='rb')
			data = gzip_stream.read()
			gzip_stream.close()
			stream.close()
	return data

@NoPickle
@interface.implementer(IS3ContentUnit)
class BotoS3ContentUnit(ContentUnit):
	"""

	.. py:attribute:: key

		The :class:`boto.s3.key.Key` for this unit.

	"""

	key = None  # Note: Boto s3.key.Key does not have good == or hash semantics, both are identity based

	def _connect_key(self):
		"""
		Ensure the key, which may have been created in a disconnected
		state, is open enough for the purposes of this object.
		"""
		if self.key and self.key.last_modified is None and self.key.bucket:
			self.key.open()

	@Lazy
	def lastModified(self):
		try:
			self._connect_key()
		except boto.exception.StorageResponseError:
			# The key is probably gone, most likely because the bucket
			# is in the process of being updated.
			logger.debug("Ignoring storage error accessing lastModified", exc_info=True)
			# Return a flag value (so that `modified` doesn't blow up). This gets cached. Alternatively,
			# we could raise AttributeError...this is mostly used dynamically with getattr and so
			# would effectively be a None?
			return -1

		return key_last_modified(self.key)

	@Lazy
	def modified(self):
		return datetime.datetime.utcfromtimestamp(self.lastModified)

	created = modified

	def make_sibling_key(self, sibling_name):
		split = self.key.name.split('/')
		split[-1] = sibling_name
		new_key = type(self.key)(bucket=self.key.bucket, name='/'.join(split))
		return new_key

	def get_parent_key(self):
		split = self.key.name.split('/')
		parent_part = split[0:-1]
		new_key = type(self.key)(bucket=self.key.bucket, name='/'.join(parent_part))
		return new_key

	def read_contents(self):
		return _read_key(self.key)

	def read_contents_of_sibling_entry(self, sibling_name):
		data = None
		if self.key:
			new_key = self.does_sibling_entry_exist(sibling_name)
			data = _read_key(new_key)
		return data

	@repoze.lru.lru_cache(None, cache=_exist_cache)  # first arg is ignored. This caches with the key (self, sibling_name)
	def does_sibling_entry_exist(self, sibling_name):
		"""
		:return: Either a Key containing some information about an existing sibling (and which is True)
			or None for an absent sibling (False).
		"""
		sib_key = self.make_sibling_key(sibling_name).name
		bucket = self.key.bucket
		try:
			return bucket.get_key(sib_key)
		except AttributeError:  # seen when we are not connected
			exc_info = sys.exc_info()
			raise boto.exception.AWSConnectionError("No connection"), None, exc_info[2]

@NoPickle
@interface.implementer(IS3ContentPackage)
class BotoS3ContentPackage(ContentPackage, BotoS3ContentUnit):

	TRANSIENT_EXCEPTIONS = (boto.exception.AWSConnectionError,)

	# XXX: Note that this needs the same lastModified fixes as
	# the filesystem version

def _package_factory(key):
	toc_key = key.bucket.get_key((key.name + '/' + eclipse.TOC_FILENAME).replace('//', '/'))

	if toc_key:
		temp_entry = BotoS3ContentUnit(key=toc_key)
		return eclipse.EclipseContentPackage(temp_entry, BotoS3ContentPackage, BotoS3ContentUnit)

@NoPickle
class _BotoS3BucketContentLibraryEnumeration(library.AbstractContentPackageEnumeration):

	def __init__(self, bucket):
		"""
		:param bucket: The bucket to enumerate.
		"""
		self._bucket = bucket

	def _package_factory(self, key):
		return _package_factory(key)

	def _possible_content_packages(self):
		return list(self._bucket.list(delimiter='/'))

@NoPickle
class BotoS3BucketContentLibrary(library.GlobalContentPackageLibrary):
	"""
	Enumerates the first level of a '/' delimited bucket and treats each
	entry as a possible content package. Content packages are cached.

	.. warning:: This is completely static right now, enumerated just once.
		We need some level of dynamism here.

	.. warning:: We probably generate content units that are invalid and incapable of
		getting their last modified dates when hrefs contain fragment identifiers, since
		those do not correspond to files in the filesystem or objects in the bucket.
	"""

	def __init__(self, bucket):
		library.GlobalContentPackageLibrary.__init__(self, _BotoS3BucketContentLibraryEnumeration(bucket))
