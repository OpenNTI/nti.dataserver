#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from nti.contentsearch.search_query import QueryObject

from nti.contentsearch.tests import SharedConfiguringTestLayer


class TestSearchQuery(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_queryobject_ctor(self):
        qo = QueryObject(term=u'term')
        assert_that(qo, has_property('term', is_(u'term')))
        assert_that(qo, has_property('query', is_(u'term')))
