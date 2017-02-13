#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope.component.hooks import setHooks

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import mock_db_trans
from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

import zope.testing.cleanup


class SharedConfiguringTestLayer(GCLayerMixin,
                                 DSInjectorMixin,
                                 ZopeComponentLayer,
                                 ConfiguringLayerMixin):

    set_up_packages = ('nti.dataserver', 'nti.app.messaging')

    @classmethod
    def setUp(cls):
        setHooks()
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        setHooks()
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass
