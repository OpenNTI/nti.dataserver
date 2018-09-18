#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A tween that pushes additional useful metrics to statsd when enabled

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
