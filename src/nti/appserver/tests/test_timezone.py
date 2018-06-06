#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from hamcrest import is_
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import assert_that
does_not = is_not

import pytz

import simplejson as json

from datetime import datetime

from six.moves.urllib_parse import quote

from zope import component

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.request_response import ByteHeadersDummyRequest as DummyRequest

from nti.app.testing.layers import AppLayerTest

from nti.appserver.interfaces import IDisplayableTimeProvider

from nti.appserver.timezone import TIMEZONE_COOKIE
from nti.appserver.timezone import TIMEZONE_ID_HEADER
from nti.appserver.timezone import TIMEZONE_OFFSET_HEADER

from nti.dataserver.tests.mock_dataserver import mock_db_trans


class TestTimeZone(AppLayerTest):

	@WithSharedApplicationMockDS(users=True)
	def test_time_zone(self):
		with mock_db_trans():
			user = self._get_user()
		request = DummyRequest()

		def get_date():
			return datetime.strptime('2010-01-01 12:03', "%Y-%m-%d %H:%M")

		base_utc_date = get_date()
		base_utc_date_tz = pytz.utc.localize(get_date())

		# No headers gives us default
		tz_provider = component.queryMultiAdapter((user, request),
												  IDisplayableTimeProvider)
		assert_that(tz_provider, not_none())
		assert_that(tz_provider.get_timezone_display_name(), is_('UTC'))
		adjusted_date = tz_provider.adjust_date(get_date())
		delta = adjusted_date - base_utc_date_tz
		assert_that(delta.seconds, is_(0))

		# Bad header gives us UTC
		request.headers[TIMEZONE_ID_HEADER] = 'America/DNE'
		tz_provider = component.queryMultiAdapter((user, request),
												  IDisplayableTimeProvider)
		assert_that(tz_provider, not_none())
		assert_that(tz_provider.get_timezone_display_name(), is_('UTC'))
		adjusted_date = tz_provider.adjust_date(get_date())
		delta = adjusted_date - base_utc_date_tz
		assert_that(delta.seconds, is_(0))
		assert_that(adjusted_date.hour, is_(12))

		# 5 hour offset (no dst)
		request.headers[TIMEZONE_ID_HEADER] = 'America/Cayman'
		request.headers[TIMEZONE_OFFSET_HEADER] = '-120'
		tz_provider = component.queryMultiAdapter((user, request),
												  IDisplayableTimeProvider)
		assert_that(tz_provider, not_none())
		assert_that(tz_provider.get_timezone_display_name(),
					is_('America/Cayman'))
		adjusted_date = tz_provider.adjust_date(get_date())
		delta = adjusted_date - base_utc_date_tz
		assert_that(delta.seconds, is_(0))
		assert_that(adjusted_date.hour, is_(7))

		# TZ offset
		request.headers.pop(TIMEZONE_ID_HEADER)
		tz_provider = component.queryMultiAdapter((user, request),
												  IDisplayableTimeProvider)
		assert_that(tz_provider, not_none())
		assert_that(tz_provider.get_timezone_display_name(), is_('GMT-2'))
		adjusted_date = tz_provider.adjust_date(get_date())
		delta = base_utc_date - adjusted_date
		assert_that(delta.seconds, is_(60 * 120))
		assert_that(adjusted_date.hour, is_(10))

		request.headers[TIMEZONE_OFFSET_HEADER] = '+120'
		tz_provider = component.queryMultiAdapter((user, request),
												  IDisplayableTimeProvider)
		assert_that(tz_provider, not_none())
		assert_that(tz_provider.get_timezone_display_name(), is_('GMT+2'))
		adjusted_date = tz_provider.adjust_date(get_date())
		delta = adjusted_date - base_utc_date
		assert_that(delta.seconds, is_(60 * 120))
		assert_that(adjusted_date.hour, is_(14))

		# Cookies take priority
		tz_json = {"offset": 300, "name":"America/Cayman"}
		tz_str = quote(json.dumps(tz_json))
		for tz_data in (tz_json, tz_str):
			request.cookies[TIMEZONE_COOKIE] = tz_data
			request.headers[TIMEZONE_ID_HEADER] = 'American/Casey'
			request.headers[TIMEZONE_OFFSET_HEADER] = '-120'
			tz_provider = component.queryMultiAdapter((user, request),
													  IDisplayableTimeProvider)
			assert_that(tz_provider, not_none())
			assert_that(tz_provider.get_timezone_display_name(),
						is_('America/Cayman'))
			adjusted_date = tz_provider.adjust_date(get_date())
			delta = adjusted_date - base_utc_date_tz
			assert_that(delta.seconds, is_(0))
			assert_that(adjusted_date.hour, is_(7))

		# Cookie offset
		tz_json = {"offset": 120, "name":""}
		tz_str = quote(json.dumps(tz_json))
		for tz_data in (tz_json, tz_str):
			request.headers.pop(TIMEZONE_ID_HEADER, None)
			request.cookies[TIMEZONE_COOKIE] = tz_data
			request.headers[TIMEZONE_OFFSET_HEADER] = '-120'
			tz_provider = component.queryMultiAdapter((user, request),
													  IDisplayableTimeProvider)
			assert_that(tz_provider, not_none())
			assert_that(tz_provider.get_timezone_display_name(), is_('GMT+2'))
			adjusted_date = tz_provider.adjust_date(get_date())
			delta = adjusted_date - base_utc_date
			assert_that(delta.seconds, is_(60 * 120))
			assert_that(adjusted_date.hour, is_(14))

		# Bad headers give us UTC
		request.cookies.pop(TIMEZONE_COOKIE)
		request.headers[TIMEZONE_ID_HEADER] = 'America/DNE'
		request.headers[TIMEZONE_OFFSET_HEADER] = '+120AAA'
		tz_provider = component.queryMultiAdapter((user, request),
												  IDisplayableTimeProvider)
		assert_that(tz_provider, not_none())
		assert_that(tz_provider.get_timezone_display_name(), is_('UTC'))
		adjusted_date = tz_provider.adjust_date(get_date())
		delta = adjusted_date - base_utc_date_tz
		assert_that(delta.seconds, is_(0))
		assert_that(adjusted_date.hour, is_(12))

