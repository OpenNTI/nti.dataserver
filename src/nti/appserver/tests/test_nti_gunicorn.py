#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# pylint: disable=protected-access
# XXX: Rewrap the long lines.
# pylint: disable=line-too-long
# XXX: JAM: Temporary.
# pylint:disable=import-error,wrong-import-order,no-name-in-module,attribute-defined-outside-init

import os

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import same_instance

import fudge

import gevent.pool
from gunicorn import config as gconfig

from pyramid.request import Request

from nti.appserver import nti_gunicorn

from nti.app.testing.request_response import ByteHeadersDummyRequest as DummyRequest
from nti.app.testing.layers import AppLayerTest

logger = __import__('logging').getLogger(__name__)

class MockConfig(object):
    is_ssl = False # added 0.17.1
    max_requests = 1000
    limit_request_line = 1024
    limit_request_fields = 1024
    limit_request_field_size = 1024
    proxy_protocol = True
    debug = False
    umask = 0
    worker_connections = 1
    settings = None
    access_log_format = ''
    workers = 2
    secure_scheme_headers = {
        "X-FORWARDED-PROTOCOL": "ssl",
        "X-FORWARDED-PROTO": "https",
        "X-FORWARDED-SSL": "on"
    }
    # As of 19.x, X-Forwarded-For is REMOVED in gunicorn; the PROXY
    # protocol obviates the need for it, however (access logs and
    # REMOTE_ADDR will still be correct). If you do not have the proxy
    # protocol, you'll have to do some logging changes; see
    # https://github.com/benoitc/gunicorn/pull/633
    #x_forwarded_for_header = 'X-FORWARDED-FOR'
    forwarded_allow_ips = '127.0.0.1'
    bind = ()
    max_requests_jitter = 0 # 19.2.1; 0 is default
    errorlog = "-" # 19.2; - is default

    def __init__(self):
        self.settings = {}

    def set(self, key, val):
        self.settings[key] = val
        if hasattr(self, key):
            setattr(self, key, val)


class MockSocket(object):

    def getsockname(self):
        # as of 19.x, the SERVER_NAME and SERVER_PORT
        # are derived from this value; before, we could get away
        # with None, now it must be a valid string
        return 'localhost:8081'

    def setblocking(self, arg):
        return None
    def fileno(self):
        return -1
    def accept(self):
        pass
    family = 1
    cfg_addr = ('', 8081)


class TestGeventApplicationWorker(AppLayerTest):

    def test_prefork(self):
        class MockWorker(object):
            pass
        MockConfig = MockWorker
        mock_worker = MockWorker()
        mock_worker.cfg = cfg = MockConfig()
        nti_gunicorn._pre_fork(1, mock_worker)
        assert_that(mock_worker, has_property('_nti_identifier', '1'))
        nti_gunicorn._post_fork(1, mock_worker)
        assert_that(os.environ, has_entry('NTI_WORKER_IDENTIFIER', '1'))
        assert_that(os.environ, has_entry('DATASERVER_ZEO_CLIENT_NAME', 'gunicorn_2'))

        cfg.forwarded_allow_ips = '*'
        nti_gunicorn._post_fork(1, mock_worker)
        assert_that(os.environ, has_entry('NTI_FORWARDED_ALLOWED_IPS', '*'))

        cfg.forwarded_allow_ips = ['1.2.3.4', '4.5.6.7']
        nti_gunicorn._post_fork(1, mock_worker)
        assert_that(os.environ, has_entry('NTI_FORWARDED_ALLOWED_IPS', '1.2.3.4,4.5.6.7'))

    @fudge.patch('gunicorn.workers.base.WorkerTmp')
    def test_postfork(self, fudge_tmp):
        fudge_tmp.is_a_stub()
        worker = nti_gunicorn.GeventApplicationWorker(None, None, MockSocket(), None, None, MockConfig, logger)
        worker._nti_identifier = '3'
        nti_gunicorn._post_fork(1, worker)

    @fudge.patch('gunicorn.workers.base.WorkerTmp')
    def test_init(self, fudge_tmp):
        fudge_tmp.is_a_stub()
        # 8 frickin arguments!
        #  age, ppid, socket, app, timeout, cfg, log
        nti_gunicorn.GeventApplicationWorker(None, None, MockSocket(), None, None, MockConfig, logger)

    @fudge.patch('gunicorn.workers.base.WorkerTmp', 'nti.appserver.nti_gunicorn.loadwsgi')
    def test_environ_parse_in_handler(self, fudge_tmp, fudge_loadwsgi):
        try:
            from cStringIO import StringIO as BytesIO
        except ImportError:
            # Python 3
            # XXX: We should probably use BytesIO everywhere, based on what we do
            # with it below.
            from io import BytesIO

        fudge_tmp.is_a_stub()
        fudge_loadwsgi.is_a_stub()
        global_conf = {}
        #  age, ppid, socket, app, timeout, cfg, log
        dummy_app = nti_gunicorn.dummy_app_factory(global_conf)
        dummy_app.app = dummy_app
        global_conf['__file__'] = ''
        global_conf['http_port'] = '1'
        worker = nti_gunicorn.GeventApplicationWorker(None, None, [MockSocket()], dummy_app, None, MockConfig, logger)
        server = nti_gunicorn.WebSocketServer(MockSocket(), dummy_app,
                                              handler_class=nti_gunicorn.GeventApplicationWorker.wsgi_handler)
        server.worker = worker

        # Be sure that everything (e.g., ssl header parsing) is set up so that the environment comes out as expected
        # First, generate a request to read
        rqst = Request.blank('/pages?format=json', environ={b'REQUEST_METHOD': b'DELETE'})
        rqst.headers['X-FORWARDED-PROTOCOL'] = 'ssl'
        rfile = BytesIO(rqst.as_bytes() + b'\r\n\r\n')

        # Now create a local handler, as if it was accepting a local connection (as in a proxy environment)
        handler = server.handler_class(None, ('127.0.0.1', 12345), server, rfile) # socket, address, server, rfile
        rline = handler.read_requestline()
        handler.read_request(rline)

        # Finally, check the resulting environment
        handler.socket = MockSocket()
        environ = handler.get_environ()

        assert_that(environ, has_entry('wsgi.url_scheme', 'https'))

        assert_that(environ, has_entry('REQUEST_METHOD', 'DELETE'))
        assert_that(environ, has_entry('PATH_INFO', '/pages'))

        # x-forwarded-for is removed in gunicorn 19.x; see MockConfig
        #rqst.headers['X-FORWARDED-FOR'] = '41.74.174.50,10.50.0.102'
        #assert_that(environ, has_entry('REMOTE_ADDR', '41.74.174.50'))

    @fudge.patch('gunicorn.workers.base.WorkerTmp',
                 'nti.appserver.nti_gunicorn.loadwsgi',
                 'gevent.socket.socket',
                 'nti.appserver.nti_gunicorn.get_current_request')
    def test_init_process(self, fudge_tmp, fudge_loadwsgi, fudge_socket, fudge_get_current_request):
        fudge_tmp.is_a_stub()
        fudge_loadwsgi.is_a_stub()
        fudge_socket.is_a_stub()
        global_conf = {}
        #  age, ppid, socket, app, timeout, cfg, log
        dummy_app = nti_gunicorn.dummy_app_factory(global_conf)
        dummy_app.app = dummy_app
        global_conf['__file__'] = ''
        global_conf['http_port'] = '1'

        cfg = gconfig.Config()

        # Default worker_connections config
        worker = nti_gunicorn.GeventApplicationWorker(None, None, [MockSocket()], dummy_app, None, cfg, logger)
        worker.init_process(_call_super=False)
        assert_that(worker, has_property('worker_connections',
                                         nti_gunicorn.GeventApplicationWorker.PREFERRED_MAX_CONNECTIONS))

        # Changed config
        dummy_app.app = dummy_app
        cfg.settings['worker_connections'].set(300)
        worker = nti_gunicorn.GeventApplicationWorker(None, None, [MockSocket()], dummy_app, None, cfg, logger)
        worker.init_process(_call_super=False)
        assert_that(worker, has_property('worker_connections', 300))

        factory = worker.server_class
        assert_that(factory, is_(nti_gunicorn._ServerFactory))

        spawn = gevent.pool.Pool()
        server = factory(MockSocket(), spawn=spawn)

        assert_that(server.pool, is_(spawn))

        worker_greenlet = server.pool.greenlet_class()
        dummy_request = DummyRequest()
        fudge_get_current_request.is_callable().returns(None).next_call().returns(dummy_request).next_call().returns(dummy_request)
        worker_greenlet.__thread_name__()
        # cached
        old = worker_greenlet.__thread_name__()
        assert_that(old, is_(same_instance(worker_greenlet.__thread_name__())))
