#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import raises
from hamcrest import calling
from hamcrest import assert_that
from hamcrest import has_property

import fudge

from zope import interface

from zope.event import notify
from pyramid.events import ContextFound

from pyramid.httpexceptions import HTTPNotFound

from pyramid.request import Request

from nti.app.i18n.views import StringsLocalizer

from nti.dataserver.interfaces import IUser

from nti.app.testing.application_webtest import ApplicationLayerTest


def adjust(request):
    notify(ContextFound(request))


class TestApplicationViews(ApplicationLayerTest):

    request = None
    view = None

    def setUp(self):
        self.request = Request.blank('/')
        self.request.environ['HTTP_ACCEPT_LANGUAGE'] = 'ru'
        self.view = StringsLocalizer(self.request)
        self.view._DOMAIN = 'nti.dataserver'

    def test_no_domain_found(self):
        self.view._DOMAIN = 'this domain should never exist'
        assert_that(calling(self.view),
                    raises(HTTPNotFound))

    @fudge.patch('nti.app.i18n.subscribers.get_remote_user',
                 'nti.app.i18n.adapters.get_remote_user')
    def test_adjust_remote_user_default(self, fake_get1, fake_get2):
        @interface.implementer(IUser)
        class User(object):
            pass

        fake_get1.is_callable().returns(User())
        fake_get2.is_callable().returns(User())

        adjust(self.request)
        # The accept header rules
        res = self.view()

        assert_that(res,
                    has_property('location',
                                 'http://localhost/app/resources/locales/ru/LC_MESSAGES/nti.dataserver.js'))
