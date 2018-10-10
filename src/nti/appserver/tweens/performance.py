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

from perfmetrics import set_statsd_client
from perfmetrics import statsd_client
from perfmetrics import statsd_client_from_uri

from zope.cachedescriptors.property import Lazy


def includeme(config):
    statsd_uri = config.registry.settings.get('statsd_uri')
    if statsd_uri:
        # Include the perfmetrices configuration if we have a statsd_uri configured for pyramid
        config.include('perfmetrics')
        
        # Set up a default statsd client for others to use
        set_statsd_client(statsd_client_from_uri(statsd_uri))

        # Add in our custom performance tween. We want to be as high up in the stack as we
        # can but stay beneath perfmetrics.tween if that was enabled.
        config.add_tween('nti.appserver.tweens.performance.performance_tween_factory',
                         under=['perfmetrics.tween', pyramid.tweens.INGRESS])


_RESPONSE_COUNTER_STATS = ['pyramid.response.%i' % k if k >= 100 else None for k in range(0, 600)]


class PerformanceHandler(object):

    def __init__(self, handler, client):
        self.handler = handler
        self.client = client

    @Lazy
    def worker_id(self):
        return os.environ['NTI_WORKER_IDENTIFIER']

    @Lazy
    def used_metric_name(self):
        return self.worker_id + '.connection_pool.used'

    @Lazy
    def free_metric_name(self):
        return self.worker_id + '.connection_pool.free'

    def __call__(self, request):
        response = None
        try:
            response = self.handler(request)
            return response
        finally:
            if self.client is not None:
                status_code = response.status_code if response else 500
                try:
                    stat = _RESPONSE_COUNTER_STATS[status_code]
                    if stat is None:
                        raise TypeError('Invalid status code' % status_code)
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
