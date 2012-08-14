#!/usr/bin/env python
"""
Generic implementations of IContentUnit functions
"""
from __future__ import print_function, unicode_literals
import os
import datetime
logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.deprecation import deprecate
from zope.cachedescriptors.property import Lazy

from nti.utils.property import alias

from .interfaces import IDelimitedHierarchyContentUnit, IDelimitedHierarchyContentPackage
from .contentunit import ContentUnit, ContentPackage
from . import library
from . import eclipse

import rfc822
import time

@interface.implementer(IDelimitedHierarchyContentUnit)
class BotoS3ContentUnit(ContentUnit):
	"""

	.. py:attribute:: key

		The :class:`boto.s3.key.Key` for this unit.

	"""

	key = None

	@Lazy
	def lastModified( self ):
		result = rfc822.parsedate_tz( self.key.last_modified )
		if result is not None:
			result = rfc822.mktime_tz(result)
			# This is supposed to be coming in rfc822 format (see boto.s3.key)
			# But it doesn't always. So try to parse it ourself if we have to
		elif self.key.last_modified:
			# 2012-05-12T23:15:24.000Z
			result = datetime.datetime.strptime( self.key.last_modified, '%Y-%m-%dT%H:%M:%S.%fZ' )
			result = time.mktime( result )
		return result


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
			new_key =  self.make_sibling_key( sibling_name )
			return new_key.get_contents_as_string()

	def does_sibling_entry_exist( self, sibling_name ):
		return self.key.bucket.get_key( self.make_sibling_key( sibling_name ).name )


@interface.implementer(IDelimitedHierarchyContentPackage)
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

	TODO: Need some level of dynamism here.
	"""

	package_factory = staticmethod(_package_factory)

	def __init__( self, bucket ):
		"""
		:param bucket: The bucket to enumerate.
		"""
		super(BotoS3BucketContentLibrary,self).__init__( list( bucket.list( delimiter='/' ) ) )
