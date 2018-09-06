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
from hamcrest import has_property
from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

from nti.app.users.model import ContextLastSeenRecord

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.coremetadata.interfaces import IContextLastSeenRecord
from nti.coremetadata.interfaces import IContextLastSeenContainer

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
            assert_that(container.get_timestamp('1'), is_not(none()))

            # coverage
            container = IContextLastSeenContainer(user)
            assert_that(IUser(container), is_(user))
            
            record = container.get('1')
            assert_that(record, has_property('username', 'rukia@bleach.com'))
            
    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_record(self):
        aizen = ContextLastSeenRecord(username=u'aizen',
                                      context=u'bleach',
                                      timestamp=1)
        assert_that(aizen,
                    validly_provides(IContextLastSeenRecord))
        assert_that(aizen,
                    verifiably_provides(IContextLastSeenRecord))
        
        ichigo = ContextLastSeenRecord(username=u'ichigo',
                                       context=u'aizen',
                                       timestamp=1)

        assert_that(sorted([ichigo, aizen]),
                    is_([aizen, ichigo]))
    
        assert_that(ichigo.__gt__(aizen), is_(True))
