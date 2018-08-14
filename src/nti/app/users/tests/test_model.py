#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

from nti.testing.matchers import verifiably_provides

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.users.interfaces import IContextLastSeenContainer

from nti.dataserver.interfaces import IUser

from nti.dataserver.tests import mock_dataserver


class TestModel(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_model(self):

        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(username=u'rukia@bleach.com',
                                     external_value={'email': u'rukia@bleach.com',
                                                     'realname': u'rukia kuchiki',
                                                     'alias': u'sode no shirayuki'})
            container = IContextLastSeenContainer(user, None)
            assert_that(container, is_not(none()))

            assert_that(container,
                        verifiably_provides(IContextLastSeenContainer))

            container.extend(('1', '2'))
            assert_that(container, has_length(2))
            # pylint: disable=too-many-function-args
            assert_that(sorted(container.contexts()), is_(['1', '2']))
            # coverage
            container = IContextLastSeenContainer(user)
            assert_that(IUser(container), is_(user))
