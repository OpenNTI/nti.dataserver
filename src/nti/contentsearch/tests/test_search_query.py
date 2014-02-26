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
		assert_that(qo.digest(), is_('3c602f4dbf6d3edddf108dda5316ab97'))
		qo.searchOn = ('note',)
		assert_that(qo.digest(), is_('4d1c2abdc06d3a5a79bdabe95d3decd1'))
		qo.searchOn = ('note', 'redaction')
		assert_that(qo.digest(), is_('1e7fe7209ca6cc50c0d0d6a22d117943'))
		qo.searchOn = ('redaction', 'note')
		assert_that(qo.digest(), is_('1e7fe7209ca6cc50c0d0d6a22d117943'))
		qo.indexid = 'xyz'
		assert_that(qo.digest(), is_('23c695bbef1e918025da86f2d281383b'))
