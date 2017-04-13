#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string

from nti.testing.time import time_monotonically_increases

import sys
import unittest
from cStringIO import StringIO

from nti.appserver.excviews import EmailReportingExceptionView
from nti.appserver.excviews import AbstractRateLimitedExceptionView

import zope.testing.loghandler

class TestExcViews(unittest.TestCase):

	def setUp(self):
		super(TestExcViews, self).setUp()
		self.log_handler = zope.testing.loghandler.Handler(self)

	def tearDown(self):
		self.log_handler.close()
		super(TestExcViews, self).tearDown()

	@time_monotonically_increases
	def test_rate_limiting_and_exception_catching(self):

		class TestView(AbstractRateLimitedExceptionView):
			# This is dependent on the log capture taking time
			# measures, so it could vary
			aux_period = 5
			aux_called = False

			def _do_create_response(self):
				raise StandardError()

			def _do_aux_action(self):
				self.aux_called = True
				raise StandardError()

		view = TestView(None, None)

		view()
		# Initially
		assert_that(view, has_property('aux_called', True))
		original_last_aux = view._last_aux_time
		assert_that(original_last_aux, not_none())
		view.aux_called = False

		# Now we have to step it two more times
		view()
		assert_that(view, has_property('aux_called', False))

		view()
		assert_that(view, has_property('_last_aux_time', original_last_aux))
		assert_that(view, has_property('aux_called', False))

		view()
		assert_that(view, has_property('aux_called', True))
		assert_that(view, has_property('_last_aux_time', original_last_aux + 7))

	def test_find_paste(self):

		from paste.exceptions.errormiddleware import ErrorMiddleware

		class Exp(Exception):
			pass

		def app(*args):
			raise Exp()

		wrapped = ErrorMiddleware(app)

		environ = {'paste.throw_errors': True}

		try:
			wrapped(environ, None)
			assert False
		except Exp as e:
			info = sys.exc_info()

		class Request(object):
			exc_info = None
			environ = None

		request = Request()
		request.exc_info = info
		request.environ = environ
		# The default configuration will report to
		# wsgi.errors, we can test that
		environ['wsgi.errors'] = StringIO()
		view = EmailReportingExceptionView(e, request)

		assert_that(view._find_exception_handler(),
					is_(wrapped.exception_handler))

		view._do_aux_action()
		assert_that(environ['wsgi.errors'].getvalue(),
					 contains_string('raise Exp'))

	def test_not_find_paste(self):

		class Exp(Exception):
			pass

		def app(*args):
			raise Exp()

		environ = {'paste.throw_errors': True}

		try:
			app(environ, None)
			assert False
		except Exp as e:
			info = sys.exc_info()

		class Request(object):
			exc_info = None
			environ = None

		request = Request()
		request.exc_info = info
		request.environ = environ

		self.log_handler.add('nti.appserver.excviews')
		view = EmailReportingExceptionView(e, request)
		view._do_aux_action()

		recs = self.log_handler.records

		assert_that(recs[0].getMessage(),
					contains_string('not reporting'))
		assert_that(recs[0].getMessage(),
					contains_string('raise Exp'))
