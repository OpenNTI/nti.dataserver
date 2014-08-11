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
from hamcrest import has_property
from hamcrest import contains

from ...tests import ContentlibraryLayerTest

from ..interfaces import IRelatedContentIndexedDataContainer
from ..interfaces import IVideoIndexedDataContainer

import os
from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary as FileLibrary

from zope import lifecycleevent

class TestSubscribers(ContentlibraryLayerTest):

	def setUp(self):
		library_dir = os.path.join( os.path.dirname(__file__), 'library' )
		self.library = FileLibrary(library_dir)

	def _do_test(self, iface,
				 unit_ntiid='tag:nextthought.com,2011-10:NTI-HTML-CourseTestContent.lesson1',
				 entry_ntiid=None):

		self.library.syncContentPackages()
		unit = self.library.pathToNTIID(unit_ntiid)[-1]

		container = iface(unit)

		assert_that( container, has_length(1) )
		assert_that( container.get_data_items(),
					 contains( has_entry('ntiid',
										 entry_ntiid) ) )

		lifecycleevent.removed(self.library[0])

		assert_that( container, has_length(0) )
		assert_that( container, has_property('lastModified', -1))

		lifecycleevent.added(self.library[0])
		lifecycleevent.modified(self.library[0])
		assert_that( container, has_length(1) )

	def test_related_work(self):
		self._do_test(IRelatedContentIndexedDataContainer,
					  entry_ntiid='tag:nextthought.com,2011-10:NTI-RelatedWorkRef-CourseTestContent.relatedworkref.0')

	def test_video(self):
		self._do_test(IVideoIndexedDataContainer,
					  entry_ntiid="tag:nextthought.com,2011-10:NTI-NTIVideo-CourseTestContent.ntivideo.video1")
