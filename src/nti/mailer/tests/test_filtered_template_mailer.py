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


from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_property


from nti.app.testing.layers  import AppLayerTest
from ..filtered_template_mailer import NextThoughtOnlyMailer
from ..filtered_template_mailer import ImpersonatedMailer
from ..interfaces import ITemplatedMailer
from ..interfaces import IPrincipal
from ..interfaces import IEmailAddressable
from ..interfaces import EmailAddresablePrincipal

from nti.testing.matchers import validly_provides

from zope import interface


class User(object):
	username = 'the_user'

class Profile(object):
	realname = 'Suzë Schwartz'

@interface.implementer(IPrincipal, IEmailAddressable)
class Principal(object):
	id = 'the_prin_id'
	email = None

from .test_default_template_mailer import Request

class _BaseMixin(object):

	mailer = None

	def test_provides(self):
		assert_that( self.mailer(),
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

		msg = self.mailer().create_simple_html_text_email('new_user_created',
													 subject='Hi there',
													 recipients=[recipient],
													 bcc=bcc,
													 template_args={'user': user, 'profile': profile, 'context': user },
													 package='nti.appserver',
													 request=request)

		msg.sender = 'foo@bar'
		base_msg = msg.to_message()
		assert_that( base_msg, has_entry('To', to) )
		return msg

	def _check(self, recipient, to, extra_environ=None, **kwargs ):
		result = self._do_check(recipient, to, extra_environ=extra_environ, **kwargs)
		if isinstance(recipient, basestring):
			prin = Principal()
			prin.email = recipient
			self._do_check(EmailAddresablePrincipal(prin), to, extra_environ=extra_environ, **kwargs)
		return result


class TestNextThoughtOnlyEmail(AppLayerTest,_BaseMixin):

	mailer = NextThoughtOnlyMailer

	def test_create_mail_message_to_nextthought(self):
		self._check( 'jason.madden@nextthought.com', 'jason.madden@nextthought.com')

	def test_create_mail_message_to_other(self):
		self._check('jamadden@ou.edu', 'dummy.email+jamadden@nextthought.com')

	def test_bcc_to_nextthought(self):
		bcc = Principal()
		bcc.email = 'bcc@foo.com'
		msg = self._check( 'jamadden@ou.edu', 'dummy.email+jamadden@nextthought.com',
						   bcc=bcc)
		assert_that( msg, has_property('bcc', ['dummy.email+bcc@nextthought.com']) )

class TestImpersonatedEmail(AppLayerTest,_BaseMixin):

	mailer = ImpersonatedMailer

	def test_create_mail_message_not_impersonated(self):
		self._check('jamadden@ou.edu', 'jamadden@ou.edu')

	def test_create_mail_message_impersonated(self):
		self._check('jamadden@ou.edu', 'dummy.email+jamadden@nextthought.com',
					{'REMOTE_USER_DATA': 'sjohnson@nextthought.com'})
