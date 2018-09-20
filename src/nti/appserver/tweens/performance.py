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

from perfmetrics import statsd_client

def performance_tween_factory(handler, registry):
    client = statsd_client()

    worker = os.environ['NTI_WORKER_IDENTIFIER']
    used_metric_name = worker + '.connection_pool.used'
    free_metric_name = worker + '.connection_pool.free'

    def handle(request):
        try:
            return handler(request)
        finally:
            if client is not None:
                connection_pool = request.environ['nti_connection_pool']
                free = connection_pool.free_count()
                used_count = connection_pool.size - free

                client.gauge(used_metric_name, used_count)
                client.gauge(free_metric_name, free)

    return handle
