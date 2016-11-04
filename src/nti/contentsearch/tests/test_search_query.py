#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from nti.contentsearch.search_query import QueryObject

from nti.contentsearch.tests import SharedConfiguringTestLayer

class TestSearchQuery(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_queryobject_ctor(self):
		qo = QueryObject(term=u'term')
		assert_that(qo.term, is_(u'term'))
		assert_that(qo.query, is_(u'term'))
		assert_that(qo.digest(), is_('fb6a1d355c683292b7c71b5980823243'))
		qo.searchOn = ('note',)
		assert_that(qo.digest(), is_('e558e610776bb4a4f5f3d289db64f94d'))
		qo.searchOn = ('note', 'redaction')
		assert_that(qo.digest(), is_('06a99f8a1958ecb9280936db814e87fc'))
		qo.searchOn = ('redaction', 'note')
		assert_that(qo.digest(), is_('06a99f8a1958ecb9280936db814e87fc'))
		qo.applyHighlights = False
		assert_that(qo.digest(), is_('8e253b8436c9392b5aced6681fd7f22b'))
