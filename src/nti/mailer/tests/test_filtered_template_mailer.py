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


from nti.app.testing.base  import SharedConfiguringTestBase
from ..filtered_template_mailer import NextThoughtOnlyMailer
from ..interfaces import ITemplatedMailer

from nti.testing.matchers import validly_provides

from zope import interface
from zope.publisher.interfaces.browser import IBrowserRequest

class User(object):
	username = 'the_user'

class Profile(object):
	realname = 'Suzë Schwartz'


@interface.implementer(IBrowserRequest)
class Request(object):
	context = None
	response = None
	application_url = 'foo'

class TestNextThoughtOnlyEmail(SharedConfiguringTestBase):

	def test_provides(self):
		assert_that( NextThoughtOnlyMailer(),
					 validly_provides(ITemplatedMailer))

	def test_create_mail_message_to_nextthought(self):

		user = User()
		profile = Profile()
		request = Request()
		request.context = user

		msg = NextThoughtOnlyMailer().create_simple_html_text_email('new_user_created',
											subject='Hi there',
											recipients=['jason.madden@nextthought.com'],
											template_args={'user': user, 'profile': profile, 'context': user },
											package='nti.appserver',
											request=request)
		msg.sender = 'foo@bar'
		base_msg = msg.to_message()
		assert_that( base_msg, has_entry('To', 'jason.madden@nextthought.com') )


	def test_create_mail_message_to_other(self):

		user = User()
		profile = Profile()
		request = Request()
		request.context = user

		msg = NextThoughtOnlyMailer().create_simple_html_text_email('new_user_created',
											subject='Hi there',
											recipients=['jamadden@ou.edu'],
											template_args={'user': user, 'profile': profile, 'context': user },
											package='nti.appserver',
											request=request)
		msg.sender = 'foo@bar'
		base_msg = msg.to_message()
		assert_that( base_msg, has_entry('To', 'dummy.email+jamadden@nextthought.com') )
