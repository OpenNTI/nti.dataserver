#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entries
from hamcrest import is_not as does_not

import unittest

import os

from perfmetrics import statsd_client
from perfmetrics import statsd_client_stack

from nti.appserver.tweens.performance import performance_tween_factory

from nti.fakestatsd import FakeStatsDClient

class TestConnectionPoolStats(unittest.TestCase):

    PREFIX = 'ds1-local'

    def _make(self, patch_socket=True, error=None, prefix=''):
        obj = FakeStatsDClient(prefix=prefix)
        return obj

    def setUp(self):
        self.client = self._make(patch_socket=True, prefix=self.PREFIX)
        statsd_client_stack.push(self.client)

    @property
    def sent(self):
        return self.client.packets

    def tearDown(self):
        statsd_client_stack.pop()

    def test_client(self):
        """
        Sanity check our setup
        """
        assert_that(statsd_client(), is_(self.client))

    def mock_request_response(self):
        class MockPool(object):
            size = 100
            used = 1

            def free_count(self):
                return self.size - self.used

        pool = MockPool()
        os.environ['NTI_WORKER_IDENTIFIER'] = 'foo'

        class DummyRequest(object):
            environ = {}

        class DummyResponse(object):
            status_code = 200
        
        request = DummyRequest()
        request.environ['nti_connection_pool'] = pool

        return request, DummyResponse()

    def sent_stats(self):
        """
        Returns a tuple of counters, and guages that were sent
        """
        guages = {}
        counters = {}
        for metric in self.sent:
            mvalue, mtype = metric.split('|')
            metric, value = mvalue.split(':')
            if mtype == 'g':
                guages[metric] = value
            elif mtype == 'c':
                counters[metric] = int(value)
        return guages, counters

    def test_tween_logs_connection_pool(self):
        request, response = self.mock_request_response()
        
        tween = performance_tween_factory(lambda x: response, None)
        tween(request)

        guages, _ = self.sent_stats()

        assert_that(guages, has_entries('ds1-local.foo.connection_pool.used', '1',
                                        'ds1-local.foo.connection_pool.free', '99'))

    def test_response_counter(self):

        request, response = self.mock_request_response()

        tween = performance_tween_factory(lambda x: response, None)
        tween(request)

        _, counters = self.sent_stats()

        assert_that(counters, has_entries('ds1-local.pyramid.response.200', 1))

        response.status_code = 500
        def doom(request):
            raise ValueError('It Dead')

        tween = performance_tween_factory(doom, None)
        try:
            tween(request)
        except ValueError:
            pass

        _, counters = self.sent_stats()
        assert_that(counters, has_entries('ds1-local.pyramid.response.200', 1,
                                          'ds1-local.pyramid.response.500', 1))

        response.status_code = 40
        tween = performance_tween_factory(lambda x: response, None)
        tween(request)

        _, counters = self.sent_stats()
        #stats haven't changed
        assert_that(len(counters), is_(2))
        assert_that(counters, has_entries('ds1-local.pyramid.response.200', 1,
                                          'ds1-local.pyramid.response.500', 1))

        
