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


import pickle
from nti.testing.matchers import validly_provides

from nti.app.testing.layers import AppLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests.mock_dataserver import mock_db_trans
from ..interfaces import IUserNotableData


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
