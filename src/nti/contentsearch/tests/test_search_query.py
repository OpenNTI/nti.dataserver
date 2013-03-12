#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest

from .._search_query import QueryObject

from hamcrest import (assert_that, is_)

class TestSearchQuery(unittest.TestCase):

	def test_queryobject_ctor(self):
		qo = QueryObject(term=u'term')
		assert_that(qo.term, is_(u'term'))
		assert_that(qo.query, is_(u'term'))
		
		qo = QueryObject(query=u'query')
		assert_that(qo.term, is_(u'query'))
		assert_that(qo.query, is_(u'query'))

	def test_queryobject_properties(self):
		d = {k: '400' for k in QueryObject.__int_properties__}
		qo = QueryObject(query=u'query', username='nt', **d)
		for k in QueryObject.__int_properties__:
			assert_that(qo[k], is_(400))
		
		assert_that(qo.limit, is_(400))
		assert_that(qo.prefix, is_(400))
		assert_that(qo.maxchars, is_(400))
		assert_that(qo.maxdist, is_(400))
		assert_that(qo.surround, is_(400))
		assert_that(qo.username, is_(u'nt'))
