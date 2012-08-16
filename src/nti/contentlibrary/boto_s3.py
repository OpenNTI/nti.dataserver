#!/usr/bin/env python
"""
Generic implementations of IContentUnit functions
"""
from __future__ import print_function, unicode_literals
import datetime
logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.cachedescriptors.property import Lazy

from nti.utils.property import alias

from .interfaces import IS3ContentUnit
from .interfaces import IS3ContentPackage
from .interfaces import IS3Bucket
from .interfaces import IS3Key
from .contentunit import ContentUnit, ContentPackage
from . import library
from . import eclipse

import rfc822
import time
import numbers
import webob.datetime_utils

# Make the boto classes fit better with Zope, including making them
# ILocation like and giving them interfaces
import boto.s3.bucket
import boto.s3.key

interface.classImplements( boto.s3.bucket.Bucket, IS3Bucket )
interface.classImplements( boto.s3.key.Key, IS3Key )
class _WithName: # NOTE: Not new-style
	__name__ = alias('name')

boto.s3.bucket.Bucket.__bases__ += _WithName,
boto.s3.bucket.Bucket.__parent__ = alias( 'connection' )

boto.s3.key.Key.__bases__ += _WithName,
boto.s3.key.Key.__parent__ = alias( 'bucket' )

def key_last_modified( key ):
	"""
	Return the last modified value of the key in some form thats actually
	useful, not a goddamn arbitrary format string.
	:return: A float, or None.
	"""
	__traceback_info__ = key, key.last_modified
	if isinstance( key.last_modified, numbers.Number ):
		return key.last_modified # Mainly for tests
	result = rfc822.parsedate_tz( key.last_modified )
	if result is not None:
		result = rfc822.mktime_tz(result)
		# This is supposed to be coming in rfc822 format (see boto.s3.key)
		# But it doesn't always. So try to parse it ourself if we have to
	elif key.last_modified:
		# 2012-05-12T23:15:24.000Z
		result = datetime.datetime.strptime( key.last_modified, '%Y-%m-%dT%H:%M:%S.%fZ' )
		result = result.replace( tzinfo=webob.datetime_utils.UTC )
		result = time.mktime( result.timetuple() )
	return result

# TODO: We need to do caching of does_sibling_entry_exist and read_contents.
# does_exist is used by appserver/censor_policies on every object creation/edit
# which quickly adds up.
# Right now, our policy for does_exist is a very simple, very dumb cache that we share
# with all content units, caching questions for 10 minutes
import repoze.lru
_exist_cache = repoze.lru.ExpiringLRUCache( 1000, default_timeout=600 )
import zope.testing.cleanup
zope.testing.cleanup.addCleanUp( _exist_cache.clear )

@interface.implementer(IS3ContentUnit)
class BotoS3ContentUnit(ContentUnit):
	"""

	.. py:attribute:: key

		The :class:`boto.s3.key.Key` for this unit.

	"""

	key = None

	def _connect_key(self):
		"""
		Ensure the key, which may have been created in a disconnected
		state, is open enough for the purposes of this object.
		"""
		if self.key and self.key.last_modified is None and self.key.bucket:
			self.key.open()

	@Lazy
	def lastModified( self ):
		self._connect_key( )
		return key_last_modified( self.key )

	@Lazy
	def modified(self):
		return datetime.datetime.utcfromtimestamp( self.lastModified )

	created = modified

	def make_sibling_key( self, sibling_name ):
		split = self.key.name.split( '/' )
		split[-1] = sibling_name
		new_key = type(self.key)( bucket=self.key.bucket, name='/'.join( split ) )
		return new_key

	def get_parent_key( self ):
		split = self.key.name.split( '/' )
		parent_part = split[0:-1]
		new_key = type(self.key)( bucket=self.key.bucket, name='/'.join( parent_part ) )
		return new_key

	def read_contents( self ):
		return self.key.get_contents_as_string()

	def read_contents_of_sibling_entry( self, sibling_name ):
		if self.key:
			new_key = self.does_sibling_entry_exist( sibling_name )
			return new_key.get_contents_as_string() if new_key else None

	@repoze.lru.lru_cache( 1, cache=_exist_cache )
	def does_sibling_entry_exist( self, sibling_name ):
		"""
		:return: Either a Key containing some information about an existing sibling (and which is True)
			or None for an absent sibling (False).
		"""
		return self.key.bucket.get_key( self.make_sibling_key( sibling_name ).name )


@interface.implementer(IS3ContentPackage)
class BotoS3ContentPackage(ContentPackage,BotoS3ContentUnit):
	pass

def _package_factory( key ):
	toc_key = key.bucket.get_key( (key.name + '/' + eclipse.TOC_FILENAME).replace( '//', '/') )

	if toc_key:
		temp_entry = BotoS3ContentUnit( key=toc_key )
		return eclipse.EclipseContentPackage( temp_entry, BotoS3ContentPackage, BotoS3ContentUnit )

class BotoS3BucketContentLibrary(library.AbstractCachedStaticLibrary):
	"""
	Enumerates the first level of a '/' delimited bucket and treats each
	entry as a possible content package. Content packages are cached.

	.. warning:: This is completely static right now, enumerated just once.
		We need some level of dynamism here.

	.. warning:: We probably generate content units that are invalid and incapable of
		getting their last modified dates when hrefs contain fragment identifiers, since
		those do not correspond to files in the filesystem or objects in the bucket.
	"""

	package_factory = staticmethod(_package_factory)

	def __init__( self, bucket ):
		"""
		:param bucket: The bucket to enumerate.
		"""
		super(BotoS3BucketContentLibrary,self).__init__( list( bucket.list( delimiter='/' ) ) )
