#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import is_
from hamcrest import has_length
from hamcrest import instance_of
from hamcrest import has_properties

import unittest

from nti.dataserver.tests.mock_statsd import MockStatsDClient
from nti.dataserver.tests.mock_statsd import Counter
from nti.dataserver.tests.mock_statsd import Gauge
from nti.dataserver.tests.mock_statsd import Timer
from nti.dataserver.tests.mock_statsd import _as_metrics


class TestStatsDParsing(unittest.TestCase):

    def test_counter(self):
        packet = 'gorets:1|c'
        metric = _as_metrics(packet)

        assert_that(metric, has_length(1))
        metric = metric[0]

        assert_that(metric, instance_of(Counter))
        assert_that(metric.name, is_('gorets'))
        assert_that(metric.value, is_('1'))
        assert_that(metric.sampling_rate, is_(none()))

    def test_sampled_counter(self):
        packet = 'gorets:1|c|@0.1'
        metric = _as_metrics(packet)

        assert_that(metric, has_length(1))
        metric = metric[0]

        assert_that(metric, instance_of(Counter))
        assert_that(metric.name, is_('gorets'))
        assert_that(metric.value, is_('1'))
        assert_that(metric.sampling_rate, is_(0.1))

    def test_timer(self):
        packet = 'glork:320|ms'
        metric = _as_metrics(packet)

        assert_that(metric, has_length(1))
        metric = metric[0]

        assert_that(metric, instance_of(Timer))
        assert_that(metric.name, is_('glork'))
        assert_that(metric.value, is_('320'))
        assert_that(metric.type, is_('ms'))
        assert_that(metric.sampling_rate, is_(none()))

    def test_timer_seconds(self):
        packet = 'glork:3|s'
        metric = _as_metrics(packet)

        assert_that(metric, has_length(1))
        metric = metric[0]

        assert_that(metric, instance_of(Timer))
        assert_that(metric.name, is_('glork'))
        assert_that(metric.value, is_('3'))
        assert_that(metric.type, is_('s'))
        assert_that(metric.sampling_rate, is_(none()))  

    def test_guage(self):
        packet = 'gaugor:+333|g'
        metric = _as_metrics(packet)

        assert_that(metric, has_length(1))
        metric = metric[0]

        assert_that(metric, instance_of(Gauge))
        assert_that(metric.name, is_('gaugor'))
        assert_that(metric.value, is_('+333'))
        assert_that(metric.sampling_rate, is_(none()))

    def test_multi_metric(self):
        packet = 'gorets:1|c\nglork:320|ms\ngaugor:333|g\nuniques:765|s'
        metrics = _as_metrics(packet)
        assert_that(metrics, contains(instance_of(Counter),
                                      instance_of(Timer),
                                      instance_of(Gauge),
                                      instance_of(Timer)))


class TestMockStatsDClient(unittest.TestCase):

    def setUp(self):
        self.client = MockStatsDClient()

    def test_tracks_metrics(self):
        self.client.incr('mycounter')
        self.client.gauge('mygauge', 5)
        self.client.timing('mytimer', 3003)

        assert_that(self.client, has_length(3))

        counter, gauge, timer = self.client.metrics

        assert_that(counter, instance_of(Counter))
        assert_that(counter, has_properties('name', 'mycounter', 'value', '1'))

        assert_that(gauge, instance_of(Gauge))
        assert_that(gauge, has_properties('name', 'mygauge', 'value', '5'))

        assert_that(timer, instance_of(Timer))
        assert_that(timer, has_properties('name', 'mytimer', 'value', '3003', 'type', 'ms'))

    def test_clear(self):
        self.client.incr('mycounter')
        assert_that(self.client, has_length(1))

        self.client.clear()
        assert_that(self.client, has_length(0))
