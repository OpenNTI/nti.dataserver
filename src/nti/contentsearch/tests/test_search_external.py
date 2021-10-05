#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import equal_to
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from nti.contentsearch.search_hits import SearchHit

from nti.contentsearch.search_query import QueryObject
from nti.contentsearch.search_query import DateTimeRange

from nti.contentsearch.search_results import SearchResults
from nti.contentsearch.search_results import SuggestResults

from nti.externalization import to_external_object

from nti.externalization.internalization import find_factory_for
from nti.externalization import update_from_external_object

from nti.contentsearch.tests import SharedConfiguringTestLayer


class TestSearchExternal(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    def test_externalize_search_results(self):
        qo = QueryObject.create(u"wind")

        hit = SearchHit()
        hit.ID = u'1'
        hit.TargetMimeType = u'foo'
        results = SearchResults(Query=qo)
        results._add_hit(hit)  # force add it

        eo = to_external_object(results)
        assert_that(eo, has_entry('Query', 'wind'))
        assert_that(eo, has_entry('Items', has_length(1)))
        assert_that(eo, has_key('HitMetaData'))

        # internalize
        factory = find_factory_for(eo)
        new_results = factory()
        update_from_external_object(new_results, eo)

        assert_that(new_results, has_property('Query', is_not(none())))
        assert_that(new_results, has_property('Hits', has_length(1)))

    def test_externalize_suggest_results(self):
        qo = QueryObject.create(u"wind")
        results = SuggestResults(Query=qo)
        results.add(u'aizen')

        eo = to_external_object(results)
        assert_that(eo, has_entry('Query', 'wind'))
        assert_that(eo, has_entry('Items', has_length(1)))

        # internalize
        factory = find_factory_for(eo)
        new_results = factory()
        update_from_external_object(new_results, eo)

        assert_that(new_results, has_property('Query', is_not(none())))
        assert_that(new_results, has_property('Suggestions', has_length(1)))

    def test_search_query(self):
        creationTime = DateTimeRange(startTime=0, endTime=100)
        qo = QueryObject(term=u"sode no shirayuki", 
                         sortOn=u'relevance', 
                         searchOn=(u'note',),
                         creationTime=creationTime, 
                         context={u'theotokos': u'Mater Dei'})
        # externalize
        eo = to_external_object(qo)
        assert_that(eo, has_entry('Class', 'SearchQuery'))
        assert_that(eo,
                    has_entry('MimeType', 'application/vnd.nextthought.search.query'))
        assert_that(eo, has_entry('sortOn', 'relevance'))
        assert_that(eo, has_entry('term', 'sode no shirayuki'))
        assert_that(eo, has_entry('searchOn', is_([u'note'])))
        assert_that(eo, has_entry('context',
                                  has_entry('theotokos', 'Mater Dei')))
        assert_that(eo, has_key('creationTime'))
        entry = eo['creationTime']
        assert_that(entry, has_entry('startTime', is_(0)))
        assert_that(entry, has_entry('endTime', is_(100)))

        # internalize
        factory = find_factory_for(eo)
        new_query = factory()
        update_from_external_object(new_query, eo)
        assert_that(new_query, has_property('term', 'sode no shirayuki'))
        assert_that(new_query, has_property('sortOn', 'relevance'))
        assert_that(new_query, has_property('searchOn', is_(['note'])))
        assert_that(new_query, has_property('creationTime',
                                            is_(equal_to(qo.creationTime))))
        assert_that(new_query, has_property('context',
                                            has_entry('theotokos', 'Mater Dei')))
