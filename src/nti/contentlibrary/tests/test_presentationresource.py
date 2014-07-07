#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import is_


from nti.testing.matchers import validly_provides

import os

from .. import filesystem
from .. import presentationresource
from ..interfaces import IDisplayablePlatformPresentationResources

class TestPresentationResource(unittest.TestCase):


	def test_discovery(self):
		absolute_path = os.path.join( os.path.dirname( __file__ ),
									  'TestFilesystem' )
		bucket = filesystem.FilesystemBucket(name='TestFilesystem')
		bucket.absolute_path = absolute_path

		package = presentationresource.DisplayableContentMixin()
		package.root = bucket

		assert_that( package, has_property('PlatformPresentationResources', has_length(3)))

		for i in package.PlatformPresentationResources:
			assert_that( i, validly_provides(IDisplayablePlatformPresentationResources))

			assert_that( i, is_(i) )
