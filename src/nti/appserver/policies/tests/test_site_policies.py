#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import contextlib

import fudge

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import contains_string
from hamcrest import has_key
from hamcrest import has_length

from quopri import decodestring

import re

import unittest


from zope import component
from zope import interface

from zope.event import notify

from nti.appserver.interfaces import UserCreatedByAdminWithRequestEvent

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener
from nti.appserver.policies.interfaces import IRequireSetPassword

from nti.appserver.policies.site_policies import GenericSitePolicyEventListener

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.tests import mock_dataserver

from nti.mailer.interfaces import IEmailAddressable

from six.moves import urllib_parse

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.testing import ITestMailDelivery


from nti.app.testing.request_response import DummyRequest

from ..site_policies import guess_site_display_name


class TestGuessSiteDisplayName(unittest.TestCase):

	def test_no_request(self):
		assert_that(guess_site_display_name(), is_("Unknown") )

	def test_fallback_to_host(self):

		request = DummyRequest.blank(b'/foo/bar/site.js')
		request.host = 'janux.nextthought.com'

		assert_that( guess_site_display_name(request), is_('Janux'))

		request.host = 'ou-alpha.nextthought.com'
		assert_that( guess_site_display_name(request), is_('Ou Alpha') )


		request.host = 'localhost:80'
		assert_that( guess_site_display_name(request), is_('Localhost') )

	@fudge.patch('nti.appserver.policies.site_policies.find_site_policy')
	def test_with_display_name(self, mock_find):
		class Policy(object):
			DISPLAY_NAME = 'Janux'
		mock_find.is_callable().returns( (Policy, None) )

		assert_that( guess_site_display_name(), is_('Janux') )


	@fudge.patch('nti.appserver.policies.site_policies.find_site_policy')
	def test_with_policy_no_display_name_no_request(self, mock_find):
		class Policy(object):
			pass
		mock_find.is_callable().returns( (Policy, None) )

		assert_that( guess_site_display_name(), is_('Unknown') )

	@fudge.patch('nti.appserver.policies.site_policies.find_site_policy')
	def test_with_policy_no_display_name_site_name(self, mock_find):
		class Policy(object):
			pass
		mock_find.is_callable().returns( (Policy, 'prmia.nextthought.com') )

		assert_that( guess_site_display_name(), is_('Prmia') )


class TestAdminCreatedUser(ApplicationLayerTest):

	def _query_params(self, url):
		url_parts = list(urllib_parse.urlparse(url))
		return dict(urllib_parse.parse_qsl(url_parts[4]))

	@WithSharedApplicationMockDS
	def test_user_is_mailed(self):
		with mock_dataserver.mock_db_trans():
			mailer = component.getUtility(ITestMailDelivery)
			del mailer.queue[:]

			user = self._create_user(u"dobby")
			addr = IEmailAddressable(user, None)
			addr.email = u'dobby@hogwarts.com'

			interface.alsoProvides(user, IRequireSetPassword)

			from nti.appserver.policies.site_policies import GenericSitePolicyEventListener
			policy = GenericSitePolicyEventListener()

			with _provide_utility(policy, ICommunitySitePolicyUserEventListener):
				request = DummyRequest()
				request.GET['success'] = 'https://nextthought.com/reset'
				notify(UserCreatedByAdminWithRequestEvent(user, request))

			assert_that(mailer.queue, has_length(1))
			msg = decodestring(mailer.queue[0].html)
			assert_that(msg,
						contains_string("A new account has been created"))

			match = re.search('href="(https://nextthought.com/reset[^"]*)"',
							 msg)
			assert_that(bool(match), is_(True))
			query_params = self._query_params(match.group(1))
			assert_that(query_params, has_key("id"))
			assert_that(query_params, has_key("username"))

	@WithSharedApplicationMockDS
	def test_user_is_not_mailed(self):
		with mock_dataserver.mock_db_trans():
			mailer = component.getUtility(ITestMailDelivery)
			del mailer.queue[:]

			user = self._create_user(u"dobby")
			addr = IEmailAddressable(user, None)
			addr.email = u'dobby@hogwarts.com'

			# Without this, no mail should go out
			# interface.alsoProvides(user, IRequireSetPassword)

			policy = GenericSitePolicyEventListener()

			with _provide_utility(policy, ICommunitySitePolicyUserEventListener):
				request = DummyRequest()
				request.GET['success'] = 'https://nextthought.com/reset'
				notify(UserCreatedByAdminWithRequestEvent(user, request))

			assert_that(mailer.queue, has_length(0))


@contextlib.contextmanager
def _provide_utility(util, iface):
	gsm = component.getGlobalSiteManager()
	gsm.registerUtility(util, iface)
	try:
		yield
	finally:
		gsm.unregisterUtility(util, iface)
