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
from hamcrest import contains_string


import nti.testing.base

from . import SharedConfiguringTestBase
from .._email_utils import create_simple_html_text_email

from zope import interface
from zope.publisher.interfaces.browser import IBrowserRequest


class TestEmail(SharedConfiguringTestBase):

	def test_create_mail_message_with_non_ascii_name(self):
		class User(object):
			username = 'the_user'

		class Profile(object):
			realname = 'Suzë Schwartz'


		@interface.implementer(IBrowserRequest)
		class Request(object):
			context = None
			response = None
			application_url = 'foo'


		user = User()
		profile = Profile()
		request = Request()
		request.context = user

		msg = create_simple_html_text_email('new_user_created_mathcounts',
											subject='Hi there',
											recipients=['jason.madden@nextthought.com'],
											template_args={'user': user, 'profile': profile, 'context': user },
											request=request)
		msg.sender = 'foo@bar'
		base_msg = msg.to_message()

		base_msg_string = str(base_msg)
		# quoted-prinatble encoding of iso-8859-1 value of umlaut-e
		assert_that( base_msg_string, contains_string('Hi=20Suz=EB=20Schwartz') )
