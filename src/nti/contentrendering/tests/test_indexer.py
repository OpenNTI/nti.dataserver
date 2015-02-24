#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import assert_that

from zope import component

from nti.contentindexing.interfaces import IBookIndexer

from . import ContentrenderingLayerTest

class TestIndexer(ContentrenderingLayerTest):

	def test_index_utils(self):
		indexer = component.getUtility(IBookIndexer)
		assert_that(indexer, is_not(None))

		indexer = component.getUtility(IBookIndexer, name="whoosh.file")
		assert_that(indexer, is_not(None))
