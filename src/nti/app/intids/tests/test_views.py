#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that

from zope import component

from zope.intid.interfaces import IIntIds

from persistent.mapping import PersistentMapping

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.interfaces import StandardExternalFields

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

import nti.dataserver.tests.mock_dataserver as mock_dataserver

INTID = StandardExternalFields.INTID
NTIID = StandardExternalFields.NTIID

class TestViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_intid_resolver(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			intids = component.getUtility(IIntIds)
			uid = intids.getId(user)
		path = '/dataserver2/@@IntIdResolver/%s' % uid
		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Class', 'User'))
		
	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_register_with_intid(self):
		with mock_dataserver.mock_db_trans(self.ds):
			data = PersistentMapping()
			mock_dataserver.current_transaction.add(data)
			intids = component.getUtility(IIntIds)
			uid = intids.queryId(data)
			assert_that(uid, is_(none()))
			oid = to_external_ntiid_oid(data)
		data = {'ntiid': oid}
		res = self.testapp.post_json('/dataserver2/@@RegisterWithIntId',
							   		 data, status=200)
		assert_that(res.json_body, has_entry(NTIID, is_(oid)))
		assert_that(res.json_body, has_entry(INTID, is_not(none())))
