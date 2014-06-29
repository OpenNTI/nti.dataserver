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
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import contains

from ...tests import ContentlibraryLayerTest

from ..interfaces import IRelatedContentIndexedDataContainer
from ..interfaces import IVideoIndexedDataContainer

import os
from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary as FileLibrary

class TestSubscribers(ContentlibraryLayerTest):

	def setUp(self):
		library_dir = os.path.join( os.path.dirname(__file__), 'library' )
		self.library = FileLibrary(library_dir)

	def test_related_work(self):
		self.library.syncContentPackages()

		unit = self.library.pathToNTIID('tag:nextthought.com,2011-10:NTI-HTML-CourseTestContent.lesson1')[-1]

		container = IRelatedContentIndexedDataContainer(unit)

		assert_that( container, has_length(1) )
		assert_that( container.get_data_items(),
					 contains( has_entry('ntiid', 'tag:nextthought.com,2011-10:NTI-RelatedWorkRef-CourseTestContent.relatedworkref.0')))

	def test_video(self):
		self.library.syncContentPackages()

		unit = self.library.pathToNTIID('tag:nextthought.com,2011-10:NTI-HTML-CourseTestContent.lesson1')[-1]

		container = IVideoIndexedDataContainer(unit)

		assert_that( container, has_length(1) )
		assert_that( container.get_data_items(),
					 contains( has_entry('ntiid',  "tag:nextthought.com,2011-10:NTI-NTIVideo-CourseTestContent.ntivideo.video1") ) )
