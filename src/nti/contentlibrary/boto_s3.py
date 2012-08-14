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
