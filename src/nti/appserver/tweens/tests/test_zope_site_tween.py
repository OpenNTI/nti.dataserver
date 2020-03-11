#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import assert_that
from hamcrest import is_

import os
import unittest

from zope import component

from nti.app.testing.request_response import DummyRequest

from nti.appserver.tweens.zope_site_tween import site_tween
from nti.appserver.interfaces import IPreferredAppHostnameProvider

logger = __import__('logging').getLogger(__name__)


class _TestPreferredHostnameProvider(object):

	def __init__(self, sub_name):
		self.sub_name = sub_name

	def get_preferred_hostname(self, unused_site_name):
		return self.sub_name


class TestZopeSiteTween(unittest.TestCase):

	def setUp(self):
		os.environ['NTI_FORWARDED_ALLOWED_IPS'] = '*'
		self.tween = site_tween(object())

	def _reset_tween(self):
		self.tween = site_tween(object())

	def test_no_preferred_host_name_header(self):
		request = DummyRequest.blank(b'/foo/bar/site.js')
		request.environ['REMOTE_ADDR'] = '127.0.0.1'
		request.host = 'janux.nextthought.com'
		self.tween._maybe_update_host_name(request)
		assert_that(request.host, is_('janux.nextthought.com'))

	def test_no_local_host(self):
		request = DummyRequest.blank(b'/foo/bar/site.js')
		request.host = 'janux.nextthought.com'
		request.environ['HTTP_X_NTI_USE_PREFERRED_HOST_NAME'] = True
		request.environ['REMOTE_ADDR'] = '192.168.1.1'
		self.tween._maybe_update_host_name(request)
		assert_that(request.host, is_('janux.nextthought.com'))

		request.environ.pop('REMOTE_ADDR')
		self.tween._maybe_update_host_name(request)
		assert_that(request.host, is_('janux.nextthought.com'))

	def test_no_preferred_host_name_provider(self):
		request = DummyRequest.blank(b'/foo/bar/site.js')
		request.environ['HTTP_X_NTI_USE_PREFERRED_HOST_NAME'] = True
		request.environ['REMOTE_ADDR'] = '127.0.0.1'
		request.host = 'janux.nextthought.com'
		self.tween._maybe_update_host_name(request)
		assert_that(request.host, is_('janux.nextthought.com'))

	def test_updated_host_name(self):
		sub_name = 'SubstituteHostname.com'
		provider = _TestPreferredHostnameProvider(sub_name)
		gsm = component.getGlobalSiteManager()
		gsm.registerUtility(provider, IPreferredAppHostnameProvider)
		try:
			request = DummyRequest.blank(b'/foo/bar/site.js')
			request.environ['HTTP_X_NTI_USE_PREFERRED_HOST_NAME'] = True
			request.environ['nti.current_site'] = 'janux.nextthought.com'
			request.environ['REMOTE_ADDR'] = '127.0.0.1'
			request.host = 'janux.nextthought.com'
			self.tween._maybe_update_host_name(request)
			assert_that(request.host, is_(sub_name))

			# Port is preserved
			request.host = 'janux.nextthought.com:8080'
			self.tween._maybe_update_host_name(request)
			assert_that(request.host, is_('%s:%s' % (sub_name, '8080')))

			# Change forwarded ips
			request.host = 'janux.nextthought.com'
			os.environ['NTI_FORWARDED_ALLOWED_IPS'] = ''
			self._reset_tween()
			self.tween._maybe_update_host_name(request)
			assert_that(request.host, is_('janux.nextthought.com'))

			os.environ['NTI_FORWARDED_ALLOWED_IPS'] = '4.3.2.1'
			request.environ['REMOTE_ADDR'] = '1.2.3.4'
			self._reset_tween()
			self.tween._maybe_update_host_name(request)
			assert_that(request.host, is_('janux.nextthought.com'))

			os.environ['NTI_FORWARDED_ALLOWED_IPS'] = '1.2.3.4'
			request.environ['REMOTE_ADDR'] = '1.2.3.4'
			self._reset_tween()
			self.tween._maybe_update_host_name(request)
			assert_that(request.host, is_(sub_name))

			os.environ['NTI_FORWARDED_ALLOWED_IPS'] = '5.6.2.3,1.2.3.4'
			request.environ['REMOTE_ADDR'] = '1.2.3.4'
			self._reset_tween()
			self.tween._maybe_update_host_name(request)
			assert_that(request.host, is_(sub_name))
		finally:
			gsm.unregisterUtility(provider, IPreferredAppHostnameProvider)
			os.environ.pop('NTI_FORWARDED_ALLOWED_IPS', None)
