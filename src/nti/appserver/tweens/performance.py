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

    def handle(request):
        try:
            return handler(request)
        finally:
            if client is not None:
                worker = os.getpid()
                connection_pool_prefix = 'connection_pool.%s' % worker
                connection_pool = request.environ['nti_connection_pool']
                free = connection_pool.free_count()
                used_count = connection_pool.size - free

                client.gauge(('%s.used' % connection_pool_prefix), used_count)
                client.gauge(('%s.free' % connection_pool_prefix), free)

    return handle
