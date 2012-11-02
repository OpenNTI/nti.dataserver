#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import same_instance
from hamcrest import has_key
from hamcrest import has_entry

from pyramid.testing import DummyRequest

import nti.tests
import socket
import gevent.pool
from nose.tools import assert_raises

from nti.appserver import gunicorn

def test_create_flash_socket():

	with assert_raises( socket.error ):
		class O(object):
			flash_policy_server_port = 1
		gunicorn._create_flash_socket( O, logger )

import fudge
class MockConfig(object):
	max_requests = None
	debug = False
	umask = 0
	worker_connections = 1
	flash_policy_server_port = 1
	settings = None
	access_log_format = ''

class MockSocket(object):

	def getsockname(self):
		return None

	def setblocking(self, arg):
		return None
	def fileno( self ):
		return -1

from gunicorn import config as gconfig

class TestGeventApplicationWorker(nti.tests.ConfiguringTestBase):

	@fudge.patch('gunicorn.workers.base.WorkerTmp')
	def test_init(self, fudge_tmp):
		fudge_tmp.is_a_stub()
		# 8 frickin arguments!
		#  age, ppid, socket, app, timeout, cfg, log
		gunicorn.GeventApplicationWorker( None, None, MockSocket(), None, None, MockConfig, logger)

	@fudge.patch('gunicorn.workers.base.WorkerTmp','nti.appserver.gunicorn.loadwsgi')
	def test_init_server(self, fudge_tmp, fudge_loadwsgi):
		fudge_tmp.is_a_stub()
		fudge_loadwsgi.is_a_stub()
		global_conf = {}
		#  age, ppid, socket, app, timeout, cfg, log
		dummy_app = gunicorn.dummy_app_factory( global_conf )
		dummy_app.app = dummy_app
		global_conf['__file__'] = ''
		global_conf['http_port'] = '1'
		worker = gunicorn.GeventApplicationWorker( None, None, MockSocket(), dummy_app, None, MockConfig, logger)
		worker._init_server()

		worker = gunicorn.GeventApplicationWorker( None, None, MockSocket(), None, None, MockConfig, logger)
		with assert_raises(Exception):
			worker._init_server()


	@fudge.patch('gunicorn.workers.base.WorkerTmp','nti.appserver.gunicorn.loadwsgi','gevent.socket.socket', 'nti.appserver.gunicorn.get_current_request')
	def test_init_process(self, fudge_tmp, fudge_loadwsgi, fudge_socket, fudge_get_current_request):
		fudge_tmp.is_a_stub()
		fudge_loadwsgi.is_a_stub()
		fudge_socket.is_a_stub()
		global_conf = {}
		#  age, ppid, socket, app, timeout, cfg, log
		dummy_app = gunicorn.dummy_app_factory( global_conf )
		dummy_app.app = dummy_app
		global_conf['__file__'] = ''
		global_conf['http_port'] = '1'

		cfg = gconfig.Config()

		worker = gunicorn.GeventApplicationWorker( None, None, MockSocket(), dummy_app, None, cfg, logger)
		worker.init_process(_call_super=False)

		factory = worker.server_class
		assert_that( factory, is_( gunicorn._ServerFactory ) )

		spawn = gevent.pool.Pool()
		server = factory( None, spawn=spawn )

		assert_that( server.pool, is_( spawn ) )

		worker_greenlet = server.pool.greenlet_class()
		dummy_request = DummyRequest()
		fudge_get_current_request.is_callable().returns( None ).next_call().returns( dummy_request ).next_call().returns( dummy_request )
		worker_greenlet.__thread_name__()
		# cached
		old = worker_greenlet.__thread_name__()
		assert_that( old, is_( same_instance( worker_greenlet.__thread_name__() ) ) )
