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
from hamcrest import has_items
from hamcrest import is_not as does_not

import unittest

import os

from pyramid.testing import DummyRequest as PyramidDummyRequest

from perfmetrics import statsd_client
from perfmetrics import statsd_client_stack

from nti.appserver.tweens.performance import performance_tween_factory

from nti.fakestatsd import FakeStatsDClient
from nti.fakestatsd.matchers import is_counter
from nti.fakestatsd.matchers import is_timer

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
        return self.client.metrics

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

        class DummyRequest(PyramidDummyRequest):
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
            if metric.kind == 'g':
                guages[metric.name] = metric.value
            elif metric.kind == 'c':
                counters[metric.name] = int(metric.value)
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
        counters = {counter: counters[counter] for counter in counters if counter.startswith('ds1-local.pyramid.response')}
        #stats haven't changed
        assert_that(len(counters), is_(2))
        assert_that(counters, has_entries('ds1-local.pyramid.response.200', 1,
                                          'ds1-local.pyramid.response.500', 1))

    def test_times_handler(self):
        request, response = self.mock_request_response()
        request.path = '/dataserver2/service'

        tween = performance_tween_factory(lambda x: response, None)
        tween(request)

        metrics = self.client.metrics
        
        assert_that(metrics, has_items(is_counter('ds1-local.nti.performance.tween.dataserver2'),
                                       is_timer('ds1-local.nti.performance.tween.dataserver2.t')))

        self.client.clear()
        request.path = '/socket.io/websocket'
        tween(request)
        metrics = self.client.metrics

        assert_that(metrics, has_items(is_counter('ds1-local.nti.performance.tween.socket-io'),
                                       is_timer('ds1-local.nti.performance.tween.socket-io.t')))

    def test_classify_request(self):

        handler = performance_tween_factory(lambda x: None, None)

        request = PyramidDummyRequest()
        
        request.path = '/dataserver2'
        assert_that(handler.classify_request(request), is_('dataserver2'))

        request.path = 'dataserver2'
        assert_that(handler.classify_request(request), is_('dataserver2'))

        request.path = '/dataserver2/foo/bar/baz'
        assert_that(handler.classify_request(request), is_('dataserver2'))

        request.path = 'dataserver2/foo/bar/baz'
        assert_that(handler.classify_request(request), is_('dataserver2'))

        request.path = ''
        assert_that(handler.classify_request(request), is_('_unknown'))

        request.path = '//' #Is this even valid????
        assert_that(handler.classify_request(request), is_('_unknown'))

        request.path = ''
        assert_that(handler.classify_request(request), is_('_unknown'))

        request.path = None
        assert_that(handler.classify_request(request), is_('_unknown'))
        

        
        

        
