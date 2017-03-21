#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
from nti.testing.matchers import verifiably_provides

import unittest

from zope.mimetype.interfaces import IContentTypeAware

from nti.contentsearch.interfaces import ISearchQuery
from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import ISuggestResults

from nti.contentsearch.search_hits import SearchHit
from nti.contentsearch.search_results import SearchResults
from nti.contentsearch.search_results import SuggestResults

from nti.contentsearch.tests import SharedConfiguringTestLayer

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


class TestSearchResults(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_search_results(self):
        qo = ISearchQuery("test")
        sr = SearchResults(Query=qo)
        assert_that(sr, is_not(None))
        assert_that(sr, verifiably_provides(ISearchResults))
        assert_that(sr, verifiably_provides(IContentTypeAware))

        hit = SearchHit()
        hit.ID = '1'
        hit.TargetMimeType = 'foo'
        sr._add_hit(hit)  # force add it

        assert_that(sr, has_length(1))

        count = 0
        for n in sr.Hits:
            assert_that(n, is_not(None))
            count = count + 1

        assert_that(count, is_(1))

    @WithMockDSTrans
    def test_suggest_results(self):
        qo = ISearchQuery("test")
        sr = SuggestResults(Query=qo)
        assert_that(sr, is_not(None))
        assert_that(sr, verifiably_provides(ISuggestResults))
        assert_that(sr, verifiably_provides(IContentTypeAware))

        sr.add('item')
        assert_that(sr, has_length(1))

        count = 0
        for n in sr.Suggestions:
            assert_that(n, is_not(None))
            count = count + 1

        assert_that(count, is_(1))

    @WithMockDSTrans
    def test_merge_search_results(self):
        qo = ISearchQuery("test")
        sr1 = SearchResults(Query=qo)
        sr2 = SearchResults(Query=qo)

        hit = SearchHit()
        hit.ID = '1'
        hit.TargetMimeType = 'foo'
        sr1._add_hit(hit)

        hit = SearchHit()
        hit.ID = '2'
        hit.TargetMimeType = 'foo'
        sr2._add_hit(hit)

        sr1 += sr2
        assert_that(sr1, has_length(2))

    @WithMockDSTrans
    def test_merge_suggest_results(self):
        qo = ISearchQuery("test")
        sr1 = SuggestResults(Query=qo)
        sr2 = SuggestResults(Query=qo)

        sr1.add('american')
        sr2.add('british')

        sr1 += sr2
        assert_that(sr1, has_length(2))
