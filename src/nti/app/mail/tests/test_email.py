#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import not_none
from hamcrest import assert_that

from zope.dottedname import resolve as dottedname

from pyramid.renderers import render

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.contentfragments.html import sanitize_user_html

def _write_to_file(name, output):
	pass

class TestEmailVerificationTemplate(ApplicationLayerTest):

	def test_render(self):
		body = """This is the body of the email. <br /> <br />
				I need everyone to come to class this week! <br />Thank you.
				"""
		body = sanitize_user_html( body )
		args = {'body': body,
				'email_to': 'jzuech3@gmail.com',
				'first_name': 'Bob',
				'sender_name': 'David Cross',
				'support_email': 'test@test.com',
				'sender_avatar_initials': 'DC',
				'sender_avatar_url': None,
				'sender_avatar_bg_color': "#F4511E",
				'context_display_name': 'History of Science',
				'support_email': 'janux@ou.edu' }

		package = dottedname.resolve('nti.app.mail.templates')

		result = render("member_email.pt",
						 args,
						 request=self.request,
						 package=package)
		_write_to_file('member_email.html', result)
		assert_that( result, not_none() )
