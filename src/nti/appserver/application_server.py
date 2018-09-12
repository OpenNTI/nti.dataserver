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

    def __init__(self):
        self.counter = 0

    def increment(self):
        self.counter += 1

    def decrement(self):
        self.counter -= 1

    def __repr__(self):
        return str(self.counter)


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
        self.request_counter = RequestCounter()

    def handle(self, *args, **kwargs):
        self.request_counter.increment()
        logger.info('Accepting request (%s/%s)',
                    self.request_counter, self.worker.worker_connections)
        try:
            return super(WebSocketServer, self).handle(*args, **kwargs)
        finally:
            self.request_counter.decrement()
            logger.info('Finishing request (%s/%s)',
                        self.request_counter, self.worker.worker_connections)
