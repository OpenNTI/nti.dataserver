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


from zc.displayname.interfaces import IDisplayNameGenerator

from zope import component
from zope import interface

from zope.component.interfaces import ISite

from zope.event import notify

from nti.appserver.interfaces import IApplicationSettings
from nti.appserver.interfaces import UserCreatedByAdminWithRequestEvent
from nti.appserver.interfaces import UserCreatedWithRequestEvent

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener
from nti.appserver.policies.interfaces import IRequireSetPassword

from nti.appserver.policies.site_policies import GenericSitePolicyEventListener

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.coremetadata.interfaces import IUser

from nti.dataserver.authorization import ROLE_ADMIN

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


class IDummyRequest(interface.Interface):
	"""
	Use for registration of our SiteNameGenerator
	"""


class AbstractAdminCreatedUser(ApplicationLayerTest):

	@property
	def event_factory(self):
		raise NotImplementedError()

	def site_name_generator(self, site_name):
		@component.adapter(ISite, IDummyRequest)
		@interface.implementer(IDisplayNameGenerator)
		class SiteNameGenerator(object):
			def __init__(self, *args, **kwargs):
				pass

			def __call__(self, *args, **kwargs):
				return site_name

		return SiteNameGenerator

	def user_displayname_generator(self):
		@component.adapter(IUser, IDummyRequest)
		@interface.implementer(IDisplayNameGenerator)
		class UserDisplayNameGenerator(object):
			def __init__(self, user, *args, **kwargs):
				self.user = user

			def __call__(self, *args, **kwargs):
				return self.user.username

		return UserDisplayNameGenerator

	def generate_user_created_event(self, user, policy, site_name="NTI",
									environ=None):
		with _provide_adapter(self.user_displayname_generator()):
			with _provide_adapter(self.site_name_generator(site_name)):
				with _provide_utility(policy, ICommunitySitePolicyUserEventListener):
					request = DummyRequest(environ=environ)

					interface.alsoProvides(request, IDummyRequest)

					settings = component.getUtility(IApplicationSettings)
					old_reset_url = settings.get('password_reset_url')
					settings['password_reset_url'] = '/login/recover/reset'
					try:
						# Trigger the process that sends the email
						notify(self.event_factory(user, request))
					finally:
						settings['password_reset_url'] = old_reset_url


class TestAdminCreatedUser(AbstractAdminCreatedUser):

	event_factory = UserCreatedByAdminWithRequestEvent

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

			admin_pass = u'temp001'
			admin_user = self._create_user("user_admin", password=admin_pass)

			policy = GenericSitePolicyEventListener()
			auth = ('%s:%s' % (admin_user.username, admin_pass)).encode('base64')
			environ={
				'REQUEST_METHOD': 'POST',
				'HTTP_AUTHORIZATION': 'Basic %s' % (auth,)
			}
			self.generate_user_created_event(user, policy, environ=environ)

			assert_that(mailer.queue, has_length(1))
			msg = decodestring(mailer.queue[0].body)

			assert_that(msg,
						contains_string("user_admin created an account for you"))
			assert_that(mailer.queue[0].subject,
						contains_string("Welcome to NTI"))

			match = re.search('Log in at (http://example.com/login/recover/reset[^ ]*)',
							 msg)
			assert_that(bool(match), is_(True))
			query_params = self._query_params(match.group(1))
			assert_that(query_params, has_key("id"))
			assert_that(query_params, has_key("username"))

			# Using an nti-admin, shouldn't use their display name
			del mailer.queue[:]
			self._assign_role(ROLE_ADMIN, admin_user.username)
			self.generate_user_created_event(user, policy, environ=environ)
			msg = decodestring(mailer.queue[0].body)

			assert_that(mailer.queue, has_length(1))
			assert_that(msg,
						contains_string("An administrator created an account for you"))
			assert_that(mailer.queue[0].subject,
						contains_string("Welcome to NTI"))

			# With updated subject
			del mailer.queue[:]

			policy.NEW_USER_CREATED_BY_ADMIN_EMAIL_SUBJECT = "Your new ${site_name} account"
			self.generate_user_created_event(user, policy, environ=environ)

			assert_that(mailer.queue, has_length(1))
			assert_that(mailer.queue[0].subject,
						contains_string("Your new NTI account"))

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

				# Trigger the process, should skip email b/c the user
				# doesn't provide IRequireSetPassword
				notify(self.event_factory(user, request))

			assert_that(mailer.queue, has_length(0))


class TestUserCreation(AbstractAdminCreatedUser):

	event_factory = UserCreatedWithRequestEvent

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
			self.generate_user_created_event(user, policy)

			assert_that(mailer.queue, has_length(1))
			msg = decodestring(mailer.queue[0].html)

			assert_that(msg,
						contains_string("Thank you for signing up for NTI"))
			assert_that(mailer.queue[0].subject,
						contains_string("Welcome to NTI"))

			# With updated subject
			del mailer.queue[:]

			policy.NEW_USER_CREATED_EMAIL_SUBJECT = "Your new ${site_name} account"
			self.generate_user_created_event(user, policy)

			assert_that(mailer.queue, has_length(1))
			assert_that(mailer.queue[0].subject,
						contains_string("Your new NTI account"))


@contextlib.contextmanager
def _provide_utility(util, iface):
	gsm = component.getGlobalSiteManager()

	old_util = component.queryUtility(iface)
	gsm.registerUtility(util, iface)
	try:
		yield
	finally:
		gsm.unregisterUtility(util, iface)
		gsm.registerUtility(old_util, iface)


@contextlib.contextmanager
def _provide_adapter(adapter):
	gsm = component.getGlobalSiteManager()

	gsm.registerAdapter(adapter)
	try:
		yield
	finally:
		gsm.unregisterAdapter(adapter)
