#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import shutil
import tempfile

from zope import component

from nti.dataserver.users import User

from nti.externalization.internalization import update_from_external_object

import nti.contentsearch as contentsearch
from nti.contentsearch._whoosh_entity_index import IWhooshEntityIndex

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans


from nti.contentsearch.tests import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_length)


class TestWhooshUserIndex(ConfiguringTestBase):

	set_up_packages = ConfiguringTestBase.set_up_packages + ( ('whoosh_entity_index.zcml', contentsearch), )

	@classmethod
	def setUpClass( cls ):
		cls.db_dir = tempfile.mkdtemp(dir="/tmp")
		os.environ['DATASERVER_DIR'] = cls.db_dir
		super(TestWhooshUserIndex,cls).setUpClass()

	@classmethod
	def tearDownClass( cls ):
		uidx_util = component.getUtility(IWhooshEntityIndex)
		uidx_util.close()
		shutil.rmtree(cls.db_dir, True)
		super(TestWhooshUserIndex, cls).tearDownClass()

	def _create_user(self, username='nt@nti.com', password='temp001', external_value=None):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password, external_value=external_value or {})
		return usr

	@WithMockDSTrans
	def test_index_users(self):
		self._create_user()
		uidx_util = component.getUtility(IWhooshEntityIndex)
		assert_that(uidx_util.index, is_not(None))
		assert_that(uidx_util.doc_count(), is_(2))
		# check publish messages (subcribe and creation)
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(2))

		# add listener should work
		user = self._create_user(username='nt2@nti.com')
		assert_that(uidx_util.doc_count(), is_(3))
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(1))

		# check all  msgs have been consumed
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(0))

		# modified listener
		external = {u'email':u'foo@bar.com'}
		update_from_external_object(user, external)
		assert_that(uidx_util.doc_count(), is_(3))
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(1))

		# delete listener
		User.delete_user('nt2@nti.com')
		assert_that(uidx_util.doc_count(), is_(2))
		msgs = list(uidx_util._pubsub.listen())
		assert_that(msgs, has_length(1))

	@WithMockDSTrans
	def test_search_users(self):
		external_value = {u'realname':u'ichigo', u'email':u'kurosaki@nti.com',
						  u'alias':u'zangetzu'}
		ichigo = self._create_user(username=u'ichigo@nti.com', external_value=external_value)
		uidx_util = component.getUtility(IWhooshEntityIndex)
		result = uidx_util.query('ichigo')
		assert_that(result, has_length(1))
		assert_that(result[0], is_(ichigo))

		for query in ('zangetzu', 'kuro', 'ic'):
			result = uidx_util.query(query)
			assert_that(result, has_length(1))
