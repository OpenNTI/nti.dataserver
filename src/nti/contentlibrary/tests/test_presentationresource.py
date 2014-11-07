#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import same_instance

import os
import unittest

from nti.contentlibrary import filesystem
from nti.contentlibrary import presentationresource
from nti.contentlibrary.bucket import _AbstractDelimitedHierarchyObject
from nti.contentlibrary.interfaces import IDisplayablePlatformPresentationResources

from nti.testing.matchers import validly_provides

class TestPresentationResource(unittest.TestCase):

	def test_discovery(self):
		absolute_path = os.path.join( os.path.dirname( __file__ ), 'TestFilesystem' )
		bucket = filesystem.FilesystemBucket(name='TestFilesystem')
		bucket.absolute_path = absolute_path
		
		package = presentationresource.DisplayableContentMixin()
		package.root = bucket
		assert_that( package, has_property('PlatformPresentationResources', has_length(3)))

		for i in package.PlatformPresentationResources:
			assert_that(i, validly_provides(IDisplayablePlatformPresentationResources))
			assert_that(i, is_(i) )

		# cache works
		v1 = package._v_PlatformPresentationResources
		assert_that( v1, has_length(3))
		v2 = package._v_PlatformPresentationResources
		assert_that( v2, has_length(3))
		assert_that( v2, same_instance(v1))
		
		# create a fake bucket w/ the same name and last modified 
		fakebucket = _AbstractDelimitedHierarchyObject(name='TestFilesystem')
		fakebucket.lastModified = bucket.lastModified
		package.root = fakebucket
		
		# cache works
		v2 = package._v_PlatformPresentationResources
		assert_that( v2, same_instance(v1))
		
		# change last modifid
		fakebucket.lastModified = 1
		v2 = package._v_PlatformPresentationResources
		assert_that( v2, is_not(same_instance(v1)))
