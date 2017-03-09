#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that

from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.dublincore.interfaces import IDCExtended

from zope.intid.interfaces import IIntIds

from zope.security.interfaces import IParticipation
from zope.security.management import endInteraction
from zope.security.management import newInteraction
from zope.security.management import restoreInteraction

from nti.coremetadata.interfaces import IRecordable

from nti.coremetadata.mixins import RecordableMixin

from nti.dataserver.users import User

from nti.recorder.index import get_transactions

from nti.recorder.utils import record_transaction

from nti.zodb.persistentproperty import PersistentPropertyHolder

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


@interface.implementer(IRecordable, IAttributeAnnotatable)
class Bleach(PersistentPropertyHolder, RecordableMixin):
    pass
        
        
class TestAdminViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_get_locked_objects(self):
        path = '/dataserver2/@@GetLockedObjects'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Total', is_(0)))
        assert_that(res.json_body, has_entry('Items', has_length(0)))

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_remove_all_trx_history(self):
        path = '/dataserver2/@@RemoveAllTransactionHistory'
        res = self.testapp.post(path, status=200)
        assert_that(res.json_body, has_entry('Recordables', is_(0)))
        assert_that(res.json_body, has_entry('RecordsRemoved', is_(0)))

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_get_user_transaction_history(self):
        path = '/dataserver2/@@UserTransactionHistory'
        res = self.testapp.get(path, params={'startTime': 0}, status=200)
        assert_that(res.json_body, has_entry('ItemCount', is_(0)))
        assert_that(res.json_body, has_entry('Items', has_length(0)))

    @mock_dataserver.WithMockDSTrans
    def test_recordable(self):
        user = User.create_user(dataserver=self.ds,
                                username='bleach@nextthought.com')
        
        endInteraction()
        try:
            newInteraction(IParticipation(user))
            ichigo = Bleach()
            current_transaction = mock_dataserver.current_transaction
            current_transaction.add(ichigo)
            record = record_transaction(ichigo, 
                                        principal=user,
                                        type_="Activation",
                                        ext_value={'bankai':True})
            assert_that(record, is_not(none()))
        finally:
            restoreInteraction()            
        
        intids = component.getUtility(IIntIds)
        assert_that(intids.queryId(record), is_not(none()))

        transactions = list(get_transactions())
        assert_that(transactions, has_length(1))
        assert_that(record, is_in(transactions))
        
        adapted = IDCExtended(ichigo)
        assert_that(adapted.creators, is_(()))
