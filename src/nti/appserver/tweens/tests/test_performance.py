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

import unittest

import os

from perfmetrics import statsd_client
from perfmetrics import statsd_client_stack

from perfmetrics.statsd import StatsdClient

from nti.appserver.tweens.performance import performance_tween_factory
from nti.appserver.tweens.performance import performance_metrics_enabled

class TestConnectionPoolStats(unittest.TestCase):

    PREFIX = 'ds1-local'

    def _make(self, patch_socket=True, error=None, prefix=''):
        obj = StatsdClient(prefix=prefix)

        if patch_socket:
            self.sent = sent = []

            class DummySocket(object):
                def sendto(self, data, addr):
                    if error is not None:
                        raise error
                    sent.append((data, addr))

            obj.udp_sock = DummySocket()

        return obj

    def setUp(self):
        self.client = self._make(patch_socket=True, prefix=self.PREFIX)

    def tearDown(self):
        statsd_client_stack.pop()

    def test_metrics_enabled(self):
        assert_that(performance_metrics_enabled(None), is_(False))
        statsd_client_stack.push(self.client)
        assert_that(performance_metrics_enabled(None), is_(True))

    def test_client(self):
        """
        Sanity check our setup
        """
        statsd_client_stack.push(self.client)
        assert_that(statsd_client(), is_(self.client))

    def test_tween_logs_connection_pool(self):

        class MockPool(object):
            size = 100
            used = 1

            def free_count(self):
                return self.size - self.used

        pool = MockPool()
        os.environ['NTI_WORKER_IDENTIFIER'] = 'foo'

        class DummyRequest(object):
            environ = {}
        
        request = DummyRequest()
        request.environ['nti_connection_pool'] = pool

        statsd_client_stack.push(self.client)
        tween = performance_tween_factory(lambda x: True, None)
        tween(request)

        # This bit can probably be abstract into a custom assertion
        guages = {}
        for metric in [x[0] for x in self.sent]:
            mvalue, mtype = metric.split('|')
            metric, value = mvalue.split(':')
            if mtype == 'g':
                guages[metric] = value

        assert_that(guages, has_entries('ds1-local.foo.connection_pool.used', '1',
                                        'ds1-local.foo.connection_pool.free', '99'))
