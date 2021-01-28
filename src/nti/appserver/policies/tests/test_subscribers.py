#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from hamcrest import assert_that
from hamcrest import not_

from zope import interface

from zope.event import notify

from nti.appserver.policies.interfaces import IRequireSetPassword

from nti.appserver.policies.tests import PoliciesTestLayer

from nti.dataserver.tests import mock_dataserver as mock_ds

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDS

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import PasswordChangedEvent

from nti.testing.matchers import verifiably_provides


class TestSubscribers(DataserverLayerTest):

    layer = PoliciesTestLayer

    @WithMockDS
    def test_password_changed(self):
        with mock_ds.mock_db_trans():
            user = User.create_user(username="hagenrd")
            interface.alsoProvides(user, IRequireSetPassword)

            assert_that(user, verifiably_provides(IRequireSetPassword))

            notify(PasswordChangedEvent(user))
            assert_that(user, not_(verifiably_provides(IRequireSetPassword)))