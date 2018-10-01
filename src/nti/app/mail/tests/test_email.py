#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import not_none
from hamcrest import assert_that

from pyramid.renderers import render

from zope.dottedname import resolve as dottedname

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.contentfragments.html import sanitize_user_html


def _write_to_file(*unused_args, **unused_kwargs):
    pass


class TestEmailVerificationTemplate(ApplicationLayerTest):

    def test_render(self):
        body = u"""This is the body of the email. <br /> <br />
                I need everyone to come to class this week! <br />Thank you.
                """
        body = sanitize_user_html(body)
        args = {'body': body,
                'email_to': 'jzuech3@gmail.com',
                'first_name': 'Bob',
                'sender_name': 'David Cross',
                'sender_avatar_initials': 'DC',
                'sender_avatar_url': None,
                'sender_avatar_bg_color': "#F4511E",
                'context_display_name': 'History of Science',
                'support_email': 'janux@ou.edu'}

        package = dottedname.resolve('nti.app.mail.templates')

        result = render("member_email.pt",
                        args,
                        request=self.request,
                        package=package)
        _write_to_file('member_email.html', result)
        assert_that(result, not_none())
