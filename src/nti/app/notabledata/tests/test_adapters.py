#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import raises
from hamcrest import calling
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import validly_provides

import pickle

from zope import component

from nti.app.notabledata.interfaces import IUserNotableData
from nti.app.notabledata.interfaces import IUserNotableDataStorage

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.layers import AppLayerTest

from nti.dataserver.activitystream_change import Change

from nti.dataserver.tests.mock_dataserver import mock_db_trans


class TestUserNotableData(AppLayerTest):

    @WithSharedApplicationMockDS(users=True)
    def test_interface(self):

        with mock_db_trans():
            user = self._get_user()
            data = component.getMultiAdapter((user, self.beginRequest()),
                                             IUserNotableData)

            assert_that(data, validly_provides(IUserNotableData))

            # Cannot be pickled
            assert_that(calling(pickle.dumps).with_args(data),
                        raises(TypeError))


class TestUserNotableDataStorage(AppLayerTest):

    @WithSharedApplicationMockDS(users=True)
    def test_interface(self):

        with mock_db_trans():
            user = self._get_user()
            data = component.getAdapter(user,
                                        IUserNotableDataStorage)

            assert_that(data, validly_provides(IUserNotableDataStorage))

    @WithSharedApplicationMockDS(users=True)
    def test_store(self):

        with mock_db_trans():
            user = self._get_user()
            data = component.getAdapter(user,
                                        IUserNotableDataStorage)

            change = Change(u'Created', user)
            change.__parent__ = None

            iid = data.store_object(change, safe=True, take_ownership=True)
            assert_that(iid, is_(not_none()))
            assert_that(change, has_property('__parent__', data))

            assert_that(calling(data.store_object).with_args(change, take_ownership=True),
                        raises(ValueError))

            data.remove_object(change)
            assert_that(change in data._owned_objects, is_(False))
