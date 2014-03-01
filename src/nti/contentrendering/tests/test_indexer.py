#!/usr/bin/env python
# -*- coding: utf-8 -*-
# $Id$

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_not

from zope import component

from nti.contentrendering import interfaces as cr_interfaces

from . import ContentrenderingLayerTest


class TestIndexer(ContentrenderingLayerTest):

	def test_index_utils(self):
		indexer = component.getUtility(cr_interfaces.IBookIndexer)
		assert_that(indexer, is_not(None))

		indexer = component.getUtility(cr_interfaces.IBookIndexer, name="whoosh.file")
		assert_that(indexer, is_not(None))
