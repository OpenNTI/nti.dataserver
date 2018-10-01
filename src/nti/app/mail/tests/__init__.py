#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

import zope.testing.cleanup

from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


class MailLayer(ZopeComponentLayer,
                ConfiguringLayerMixin,
                DSInjectorMixin):

    set_up_packages = ('nti.dataserver', 'nti.app.mail',)

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass


import unittest


class MailLayerTest(DataserverLayerTest):
    layer = MailLayer
