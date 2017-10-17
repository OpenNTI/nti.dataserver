#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from zope import component

from zope.traversing.interfaces import ITraversable

from pyramid.testing import DummyRequest

from nti.dataserver.interfaces import UNAUTHENTICATED_PRINCIPAL_NAME

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IAnonymousUser

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


class TestTraversal(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=False, testapp=False)
    def test_anonymous_user(self):

        with mock_dataserver.mock_db_trans(self.ds):
            dataserver = component.getUtility(IDataserver)
            users_folder = IShardLayout(dataserver).users_folder
            traversable = ITraversable(users_folder)
            obj = traversable.traverse(UNAUTHENTICATED_PRINCIPAL_NAME, '')
            assert_that(IAnonymousUser.providedBy(obj), is_(True))

            traversable = ITraversable(users_folder, DummyRequest())
            obj = traversable.traverse(UNAUTHENTICATED_PRINCIPAL_NAME, '')
            assert_that(IAnonymousUser.providedBy(obj), is_(True))
