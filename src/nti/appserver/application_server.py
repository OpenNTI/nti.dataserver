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

    @property
    def pool_size(self):
        return self.server.worker.worker_connections

    def increment(self):
        self.count += 1
        self.current_count += 1

    def decrement(self):
        self.current_count -= 1

    def __repr__(self):
        return str(self.current_count)

    def __enter__(self):
        self.increment()

    def __exit__(self, *args):
        self.decrement()


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
        # Stash a request worker in the environ that will give us status on
        # how our connection pool is being used (see nti_gunicorn.py).
        self.request_counter = RequestCounter(self)
        self.environ['nti_request_counter'] = self.request_counter

    def handle(self, *args, **kwargs):
        with self.request_counter:
            return super(WebSocketServer, self).handle(*args, **kwargs)
