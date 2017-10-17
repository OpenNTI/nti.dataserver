#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import not_none
from hamcrest import assert_that

import datetime

import isodate

from zope.dottedname import resolve as dottedname

from pyramid.renderers import render

from nti.app.testing.application_webtest import ApplicationLayerTest


def _write_to_file(name, output):
    pass


class TestEmailVerificationTemplate(ApplicationLayerTest):

    def test_render(self):
        args = {'profile': 'profile',
                'token': 'ABCDEFGHI',
                'user': 'josh zuech',
                'href': 'href://link_to_verification',
                'support_email': 'test@test.com',
                'informal_username': 'Josh',
                'today': isodate.date_isoformat(datetime.datetime.now())}

        package = dottedname.resolve('nti.app.users.templates')

        result = render("email_verification_email.pt",
                        args,
                        request=self.request,
                        package=package)
        _write_to_file('email_verification.html', result)
        assert_that(result, not_none())
