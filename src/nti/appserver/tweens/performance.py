#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A tween providing a location for request-aware or request-triggered 
performance instrumentation.

This tween should be installed beneath the `perfmetrics` tween as
it does not establish a statsd client.

This tween instruments the following metrics:

 - <workerid>.connection_pool.used : The number of low level connections currently being used for the given worker
 - <workerid>.connection_pool.free : The number of remaining connections for the given worker.

.. note:: workerid is filled in from the environment variable `NTI_WORKER_IDENTIFIER`.
          This is environment is established when the worker is initially forked.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

import pyramid

from perfmetrics import Metric
from perfmetrics import set_statsd_client
from perfmetrics import statsd_client
from perfmetrics import statsd_client_from_uri

from zope.cachedescriptors.property import Lazy


def includeme(config):
    statsd_uri = config.registry.settings.get('statsd_uri')
    if statsd_uri:
        # Set up a default statsd client for others to use
        set_statsd_client(statsd_client_from_uri(statsd_uri))

        # Add in our custom performance tween. We want to be as high up in the stack as we
        # can but stay beneath perfmetrics.tween if that was enabled.
        config.add_tween('nti.appserver.tweens.performance.performance_tween_factory',
                         under=['perfmetrics.tween', pyramid.tweens.INGRESS])


_RESPONSE_COUNTER_STATS = ['pyramid.response.%i' % k if k >= 100 else None for k in range(0, 600)]

_UNKNOWN_PATH_CLASSIFIER = '_unknown'

class PerformanceHandler(object):

    def __init__(self, handler, client):
        self.handler = handler
        self.client = client
        self._handler_metric_names = {}

    @Lazy
    def worker_id(self):
        return os.environ['NTI_WORKER_IDENTIFIER']

    @Lazy
    def used_metric_name(self):
        return self.worker_id + '.connection_pool.used'

    @Lazy
    def free_metric_name(self):
        return self.worker_id + '.connection_pool.free'

    def classify_request(self, request):
        """
        Classifies the request for segmenting the count
        and timing metric we wrap around our handler. Currently
        the request is segmented by the root path segment which in practice
        results in segmenting by `dataserver2` or `socket.io`. This
        hueristic may change in the future.
        """

        # Basically we want the first path segment. The more readable way
        # to do this is split by the path seperator and take the first
        # non empty segment. This implementation is a bit more complicated
        # but is much faster. 3x as fast, using timeit, (500ns vs 1680ns)
        # when the path has several segments, and 2x as fast for paths with few segments
        path = request.path or ''
        seperator_index = path.find('/')
        # no seperator we return the path or _UNKNOWN_PATH_CLASSIFIER
        if seperator_index == -1:
            return path or _UNKNOWN_PATH_CLASSIFIER

        # Skip the leading slash
        start = 1 if seperator_index == 0 else 0

        # End at the seperator we found, unless it is a leading slash, in which case we
        # need the next slash
        end = seperator_index if seperator_index != 0 else path.find('/', 1)

        # If there wasn't another slash go to the end
        if end < 0:
            end = None
        return path[start:end] or _UNKNOWN_PATH_CLASSIFIER

    def metric_name_for_wrapping_handler(self, request):
        classifier = self.classify_request(request)

        # We expect only a few different classifiers so we cache
        # so we cache these to avoid string formatting when necessary
        metric_name = None
        if classifier in self._handler_metric_names:
            metric_name = self._handler_metric_names[classifier]
        else:
            metric_name = 'nti.performance.tween.%s' % classifier.replace('.', '-')
            self._handler_metric_names[classifier] = metric_name

        return metric_name

    def __call__(self, request):
        response = None
        try:
            with Metric(self.metric_name_for_wrapping_handler(request)):
                response = self.handler(request)
            return response
        finally:
            if self.client is not None:
                status_code = response.status_code if response else 500
                try:
                    stat = _RESPONSE_COUNTER_STATS[status_code]
                    if stat is None:
                        raise TypeError('Invalid status code %i' % status_code)
                    self.client.incr(stat)
                except (TypeError, IndexError):
                    # Unexpected response code...
                    logger.exception('Unexpected response status code %s, not sending stats', status_code)
                    
                connection_pool = request.environ['nti_connection_pool']
                free = connection_pool.free_count()
                used_count = connection_pool.size - free

                self.client.gauge(self.used_metric_name, used_count)
                self.client.gauge(self.free_metric_name, free)

        
def performance_tween_factory(handler, registry):
    client = statsd_client()

    return PerformanceHandler(handler, client)
