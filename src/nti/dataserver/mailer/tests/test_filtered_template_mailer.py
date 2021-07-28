#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property

from zope import component
from zope import interface

from zope.publisher.interfaces.browser import IBrowserRequest

from nti.app.testing.layers  import AppLayerTest

from nti.app.testing.testing import ITestMailDelivery

from nti.dataserver.mailer.filtered_template_mailer import ImpersonatedMailer
from nti.dataserver.mailer.filtered_template_mailer import NextThoughtOnlyMailer

from nti.mailer.interfaces import IPrincipal
from nti.mailer.interfaces import ITemplatedMailer
from nti.mailer.interfaces import IEmailAddressable
from nti.mailer.interfaces import EmailAddresablePrincipal

from nti.testing.matchers import validly_provides


@interface.implementer(IBrowserRequest)
class Request(object):
	context = None
	response = None
	application_url = 'foo'

	def __init__(self):
		self.annotations = {}

	def get(self, key, default=None):
		return default


class User(object):
	username = 'the_user'

class Profile(object):
	realname = u'Suzë Schwartz'

@interface.implementer(IPrincipal, IEmailAddressable)
class Principal(object):
	id = 'the_prin_id'
	email = None


class _BaseMixin(object):

	mailer = None

	def test_provides(self):
		assert_that(self.mailer(),
					 validly_provides(ITemplatedMailer))

	def _do_check(self, recipient, to, bcc=(), extra_environ=None):
		user = User()
		profile = Profile()
		request = Request()
		request.context = user
		if extra_environ:
			# Don't assign if not present, test we can deal
			# with no attribute
			request.environ = extra_environ
		token_url = 'url_to_verify_email'
		delivery = component.getUtility(ITestMailDelivery)
		del delivery.queue[:]
		msg = self.mailer().queue_simple_html_text_email(
													'test_new_user_created',
													subject='Hi there',
													recipients=[recipient],
													bcc=bcc,
													template_args={
																'user': user,
																'profile': profile,
																'verify_href': '',
																'context': user,
																'site_name': u'Test Site',
																'href': token_url,
																'support_email': 'support_email' },
													request=request)

		queued = delivery.queue[0]
		assert_that(queued, has_entry('To', to))
		return msg

	def _check(self, recipient, to, extra_environ=None, **kwargs):
		result = self._do_check(recipient, to, extra_environ=extra_environ, **kwargs)
		if isinstance(recipient, basestring):
			prin = Principal()
			prin.email = recipient
			self._do_check(EmailAddresablePrincipal(prin), to, extra_environ=extra_environ, **kwargs)
		return result

class TestNextThoughtOnlyEmail(AppLayerTest, _BaseMixin):

	mailer = NextThoughtOnlyMailer

	def test_create_mail_message_to_nextthought(self):
		whitelist = ('jason.madden@nextthought.com',
					 'ntiqatesting@gmail.com',
					 'ntiqatesting+111@gmail.com',
					 'emailusertesting@gmail.com')
		for email in whitelist:
			self._check(email, email)

	def test_create_mail_message_to_other(self):
		self._check('jamadden@ou.edu', 'dummy.email+jamadden@nextthought.com')

	def test_bcc_to_nextthought_realname(self):
		bcc = Principal()
		bcc.email = 'Name <bcc@foo.com>'
		msg = self._check('jamadden@ou.edu', 'dummy.email+jamadden@nextthought.com',
						   bcc=bcc)
		assert_that(msg, has_property('bcc', ['Name <dummy.email+bcc@nextthought.com>']))

	def test_bcc_to_nextthought_no_realname(self):
		bcc = Principal()
		bcc.email = 'bcc@foo.com'
		msg = self._check('jamadden@ou.edu', 'dummy.email+jamadden@nextthought.com',
						   bcc=bcc)
		assert_that(msg, has_property('bcc', ['dummy.email+bcc@nextthought.com']))

class TestImpersonatedEmail(AppLayerTest, _BaseMixin):

	mailer = ImpersonatedMailer

	def test_create_mail_message_not_impersonated(self):
		self._check('jamadden@ou.edu', 'jamadden@ou.edu')

	def test_create_mail_message_impersonated(self):
		userdata = {'username': 'sjohnson@nextthought.com'}
		identity = {'userdata': userdata}
		self._check('jamadden@ou.edu', 'dummy.email+jamadden@nextthought.com',
					{'repoze.who.identity': identity})
