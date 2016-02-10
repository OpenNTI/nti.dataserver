#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import not_none

from nti.dataserver.tests import mock_dataserver
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDS

from nti.dataserver.users import User

from ..zope_security_interaction_tween import security_interaction_tween_factory

from zope.security.management import queryInteraction

def _interaction_verifying_handler( request ):
	assert_that(queryInteraction(), not_none())

class MockRequest(object):
	authenticated_userid = None

class TestInteractionTween(DataserverLayerTest):

	@WithMockDS
	def test_interaction_for_authenticated_user( self ):
		interaction_factory = security_interaction_tween_factory

		handler = _interaction_verifying_handler

		request = MockRequest()
		request.authenticated_userid = 'foo@bar'

		with mock_dataserver.mock_db_trans(self.ds):
			user1 = User.create_user( self.ds, username='foo@bar', password='temp001' )

			interaction_factory(handler, None)(request)

	def test_interaction_for_anonymous_user( self ) :
		interaction_factory = security_interaction_tween_factory

		handler = _interaction_verifying_handler

		request = MockRequest()
		request.authenticated_userid = ''
		
		interaction_factory(handler, None)(request)	


