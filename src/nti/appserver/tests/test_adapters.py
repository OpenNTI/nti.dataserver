#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from pyramid.interfaces import IRequest

from zc.displayname.interfaces import IDisplayNameGenerator

from zope import component
from zope import interface

from nti.dataserver.activitystream_change import Change

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.request_response import DummyRequest


class ITestChangeContext(interface.Interface):
    pass


@interface.implementer(ITestChangeContext)
class ChangeContext(object):
    pass


def _change_context_display_name(unused_context, unused_request):
    return lambda: 'MyDisplayName'


class MockChange(Change):

    @property
    def object(self):
        return self.objectReference


class TestAdapters(ApplicationLayerTest):

    def test_change_display_name(self):
        """
        Validate we get our change.context IDisplayNameGenerator instead
        of the DefaultDisplayNameGenerator that returns `change.__name__`.
        """
        gsm = component.getGlobalSiteManager()
        gsm.registerAdapter(_change_context_display_name,
                            (ITestChangeContext, IRequest),
                            IDisplayNameGenerator)

        request = DummyRequest()
        context = ChangeContext()
        change = MockChange(Change.CREATED, context)
        change.__name__ = 'ShouldNotBeDisplayed'
        generator = component.queryMultiAdapter((change,
                                                 request),
                                                IDisplayNameGenerator)
        assert_that(generator(), is_('MyDisplayName'))
