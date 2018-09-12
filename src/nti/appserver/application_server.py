#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of network servers.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent.pywsgi

import geventwebsocket.handler


class RequestCounter(object):

    def __init__(self, server):
        self.count = 0
        self.current_count = 0
        self.server = server

    def increment(self):
        self.count += 1
        self.current_count += 1

    def decrement(self):
        self.current_count -= 1

    def __repr__(self):
        return str(self.current_count)


class _RequestContextManager(object):

    def __init__(self, server, request_counter):
        self.request_counter = request_counter
        self.server = server
        self.request_id = request_counter.count

    def __enter__(self):
        self.request_counter.increment()
        logger.info('Accepting request (request_id=%s) (%s/%s)',
                    self.request_id,
                    self.request_counter.current_count,
                    self.server.worker.worker_connections)

    def __exit__(self, *args):
        self.request_counter.decrement()
        logger.info('Finishing request (request_id=%s) (%s/%s)',
                    self.request_id,
                    self.request_counter.current_count,
                    self.server.worker.worker_connections)


# In gevent 1.0, gevent.wsgi is an alias for WSGIServer
class WebSocketServer(gevent.pywsgi.WSGIServer):
    """
    HTTP server that can handle websockets.
    """

    handler_class = geventwebsocket.handler.WebSocketHandler

    def __init__(self, *args, **kwargs):
        """
        :raises ValueError: If a ``handler_class`` keyword argument is supplied
                that specifies a non-:class:`geventwebsocket.handler.WebSocketHandler` subclass.
                That type of handler is required for websockets to work.
        """
        super(WebSocketServer, self).__init__(*args, **kwargs)
        if not issubclass(self.handler_class, geventwebsocket.handler.WebSocketHandler):
            raise ValueError("Unable to run with a handler that is not a type of %s",
                             WebSocketServer.handler_class)
        self.request_counter = RequestCounter(self)

    def handle(self, *args, **kwargs):
        with _RequestContextManager(self, self.request_counter):
            return super(WebSocketServer, self).handle(*args, **kwargs)
