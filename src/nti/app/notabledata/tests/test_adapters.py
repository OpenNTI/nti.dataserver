#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from zope import component

import unittest
from hamcrest import assert_that
from hamcrest import calling
from hamcrest import raises
from hamcrest import not_none
from hamcrest import has_property
from hamcrest import is_


import pickle
from nti.testing.matchers import validly_provides

from nti.app.testing.layers import AppLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests.mock_dataserver import mock_db_trans
from ..interfaces import IUserNotableData
from ..interfaces import IUserNotableDataStorage

from nti.dataserver.activitystream_change import Change

class TestUserNotableData(AppLayerTest):

	@WithSharedApplicationMockDS(users=True)
	def test_interface(self):

		with mock_db_trans():
			user = self._get_user()
			data = component.getMultiAdapter( (user, self.beginRequest()),
											  IUserNotableData )

			assert_that( data, validly_provides(IUserNotableData) )

			# Cannot be pickled
			assert_that( calling(pickle.dumps).with_args(data),
						 raises(TypeError) )


class TestUserNotableDataStorage(AppLayerTest):

	@WithSharedApplicationMockDS(users=True)
	def test_interface(self):

		with mock_db_trans():
			user = self._get_user()
			data = component.getAdapter( user,
										 IUserNotableDataStorage )

			assert_that( data, validly_provides(IUserNotableDataStorage) )

	@WithSharedApplicationMockDS(users=True)
	def test_store(self):

		with mock_db_trans():
			user = self._get_user()
			data = component.getAdapter( user,
										 IUserNotableDataStorage )

			change = Change('Created', user)
			change.__parent__ = None

			iid = data.store_object(change, safe=True, take_ownership=True)
			assert_that( iid, is_(not_none() ))
			assert_that( change, has_property('__parent__', data))

			assert_that( calling(data.store_object).with_args(change, take_ownership=True),
						 raises(ValueError))
