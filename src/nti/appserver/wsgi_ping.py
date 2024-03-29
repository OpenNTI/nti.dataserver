#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple ping paste filter that does nothing but return a 200.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

logger = __import__('logging').getLogger(__name__)


class PingHandler(object):
    """
    Handles the ``/_ops/ping`` url exactly.
    """

    def __init__(self, app):
        self.captured = app

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'] == '/_ops/ping':
            start_response('200 OK', [('Content-Type', 'text/plain')])
            result = ("",)
        else:
            result = self.captured(environ, start_response)
        return result


def ping_handler_factory(app, unused_global_conf=None):
    """
    Paste factory for :class:`PingHandler`
    """
    result = PingHandler(app)
    return result
