#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from nti.contentlibrary.indexed_data.catalog import create_library_catalog

from nti.contentlibrary.tests import ContentlibraryLayerTest

class TestCatalog(ContentlibraryLayerTest):
	
	def test_catalog(self):
		catalog = create_library_catalog()

		catalog.container_index.do_index_doc(1, ('a','b'))
		assert_that(list(catalog.get_references(container_ntiids='a')), is_([1]))
		
		catalog.unindex_doc(1)
		assert_that(list(catalog.get_references(container_ntiids='b')), is_([]))
		assert_that(list(catalog.get_references(container_ntiids='a')), is_([]))

		catalog.container_index.do_index_doc(1, ('x','y'))
		assert_that(catalog.get_containers(1), has_length(2))
		
		catalog.update_containers(1, ('z',))
		assert_that(catalog.get_containers(1), has_length(3))
		
		catalog.update_containers(1, ('z',))
		assert_that(catalog.get_containers(1), has_length(3))
		
		catalog.remove_containers(1, ('x','y'))
		assert_that(catalog.get_containers(1), has_length(1))
		
		catalog.remove_all_containers(1)
		assert_that(catalog.get_containers(1), has_length(0))
