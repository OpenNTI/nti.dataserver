#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from ..search_query import QueryObject

from . import SharedConfiguringTestLayer

class TestSearchQuery(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def test_queryobject_ctor(self):
		qo = QueryObject(term=u'term')
		assert_that(qo.term, is_(u'term'))
		assert_that(qo.query, is_(u'term'))
		assert_that(qo.digest(), is_('801a344e2fcdefaa3b1a7404ac4cb298'))
		qo.searchOn = ('note',)
		assert_that(qo.digest(), is_('5e3f199f05ac538a1056457e01064134'))
		qo.searchOn = ('note', 'redaction')
		assert_that(qo.digest(), is_('dc21e26578516fe69dcb93f9f7098dd0'))
		qo.searchOn = ('redaction', 'note')
		assert_that(qo.digest(), is_('dc21e26578516fe69dcb93f9f7098dd0'))
		qo.indexid = 'xyz'
		assert_that(qo.digest(), is_('4c4588d0b93044fedb32eb50ced00d18'))
