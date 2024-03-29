#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch.interfaces import ISearchQuery

from nti.contentsearch.search_utils import create_queryobject

from nti.contentsearch.tests import SharedConfiguringTestLayer

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


class TestSearchUtils(unittest.TestCase):

    layer = SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_create_query_object_accept(self):
        ntiid = make_ntiid(nttype=u'hollow', specific=u'vastolorde')
        params = {
            'accept': u'application/vnd.nextthought.note,application/vnd.nextthought.forums.personalblogentrypost',
            'term': u'menos', 
            'ntiid': ntiid
        }
        qo = create_queryobject(u'harribel@bleach.com', params)
        assert_that(ISearchQuery.providedBy(qo), is_(True))
        assert_that(qo.username, is_('harribel@bleach.com'))
        assert_that(qo.term, is_('menos'))
        assert_that(qo.origin, is_(ntiid))
        assert_that(sorted(qo.searchOn),
                    is_(['application/vnd.nextthought.forums.personalblogentrypost',
                         'application/vnd.nextthought.note']))

    @WithMockDSTrans
    def test_create_query_object_sample(self):
        ntiid = make_ntiid(nttype='hollow', specific='vastolorde')
        params = {'term': u'arrancar', 'ntiid': ntiid}
        qo = create_queryobject(u'ulquiorra@bleach.com', params)
        assert_that(ISearchQuery.providedBy(qo), is_(True))
        assert_that(qo.username, is_('ulquiorra@bleach.com'))
        assert_that(qo.term, is_('arrancar'))
        assert_that(qo.origin, is_(ntiid))

    @WithMockDSTrans
    def test_create_query_object_badnumbers(self):
        ntiid = make_ntiid(nttype=u'hollow', specific=u'vastolorde')
        params = {'term': u'arrancar', 'ntiid': ntiid}
        try:
            create_queryobject(u'ulquiorra@bleach.com', params)
            self.fail()
        except:
            pass
        
    @WithMockDSTrans
    def test_query_pac(self):
        ntiid = make_ntiid(nttype=u'hollow', specific=u'vastolorde')
        params = {
            'exclude': u'application/vnd.nextthought.redaction',
            'accept': 
                u'application/vnd.nextthought.bookcontent,application/vnd.nextthought.highlight,' +
                u'application/vnd.nextthought.note,application/vnd.nextthought.forums.personalblogentrypost,' +
                u'application/vnd.nextthought.forums.personalblogcomment,application/vnd.nextthought.messageinfo',
            'sortOn': u'relevance',
            'sortOrder': u'descending',
            'term': u'arrancar', 
            'ntiid': ntiid
        }
        qo = create_queryobject(u'ulquiorra@bleach.com', params)
        assert_that(qo.username, is_('ulquiorra@bleach.com'))
        assert_that(qo.term, is_('arrancar'))
        assert_that(qo.origin, is_(ntiid))
        assert_that(qo.sortOn, 'relevance')
        assert_that(qo.sortOrder, 'descending')
        assert_that(qo.searchOn, has_length(greater_than_or_equal_to(5)))

    @WithMockDSTrans
    def test_query_times(self):
        ntiid = make_ntiid(nttype=u'hollow', specific=u'vastolorde')
        params = {'createdAfter': 100,
                  'createdBefore': 125.5,
                  'modifiedAfter': 101,
                  'modifiedBefore': 135.5,
                  'term': u'arrancar', 'ntiid': ntiid}
        qo = create_queryobject(u'ulquiorra@bleach.com', params)
        assert_that(qo,
                    has_property('creationTime',
                                 has_property('startTime', is_(100))))
        assert_that(qo,
                    has_property('creationTime',
                                 has_property('endTime', is_(125.5))))

        assert_that(qo,
                    has_property('modificationTime',
                                 has_property('startTime', is_(101))))

        assert_that(qo,
                    has_property('modificationTime',
                                 has_property('endTime', is_(135.5))))
