#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from nti.contentlibrary.indexed_data.index import ContainedObjectCatalog

from nti.contentlibrary.tests import ContentlibraryLayerTest

class TestIndex(ContentlibraryLayerTest):

	def test_catalog(self):
		catalog = ContainedObjectCatalog()
		catalog.index(1, container_ntiids='x')
		assert_that(list(catalog.get_references(container_ntiids='x')), is_([1]))
		catalog.index(1, container_ntiids='y')
		assert_that(list(catalog.get_references(container_ntiids='x')), is_([1]))
		assert_that(list(catalog.get_references(container_ntiids='y')), is_([1]))

		catalog.unindex(1)
		assert_that(list(catalog.get_references(container_ntiids='x')), is_([]))
		assert_that(list(catalog.get_references(container_ntiids='y')), is_([]))

		catalog.unindex(10)
		assert_that(list(catalog.get_references(container_ntiids='x')), is_([]))

		catalog.index(10, container_ntiids='x')
		catalog.index(11, container_ntiids='x')
		assert_that(list(catalog.get_references(container_ntiids='x')), is_([10, 11]))
		
		catalog.unindex(10)
		assert_that(list(catalog.get_references(container_ntiids='x')), is_([11]))
		
		catalog.index(100, container_ntiids='x', namespace='p')
		assert_that(list(catalog.get_references(container_ntiids='x', namespace='p')), is_([100]))
		assert_that(list(catalog.get_references(container_ntiids='x', namespace='x')), is_([]))
		assert_that(list(catalog.get_references(container_ntiids='r', namespace='p')), is_([]))
		assert_that(list(catalog.get_references(namespace='p')), is_([100]))
		
		# indexing with a None does not alter the index
		catalog.index(100, namespace=None)
		assert_that(list(catalog.get_references(namespace='p')), is_([100]))
