#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import nti.store as store
import nti.appserver as appserver
import nti.dataserver as dataserver

from nti.dataserver.tests.mock_dataserver import SharedConfiguringTestBase as DSSharedConfiguringTestBase

class ConfiguringTestBase(DSSharedConfiguringTestBase):
	set_up_packages = (dataserver, store, ('configure_invitations.zcml', appserver)) + (('purchasables.zcml', 'nti.store.tests'),)


from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import mock_db_trans

from nti.testing.layers import find_test
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

class SharedConfiguringTestLayer(ZopeComponentLayer,
								 GCLayerMixin,
								 ConfiguringLayerMixin,
								 DSInjectorMixin):

	set_up_packages = ('nti.dataserver', 'nti.store',
					   ('configure_invitations.zcml', 'nti.appserver'),
					   ('purchasables.zcml', 'nti.store.tests'),
					   ('courses.zcml', 'nti.store.tests'))

	@classmethod
	def setUp(cls):
		cls.setUpPackages()

	@classmethod
	def tearDown(cls):
		cls.tearDownPackages()

	@classmethod
	def testSetUp(cls, test=None):
		cls.setUpTestDS(test)
