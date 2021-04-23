#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import unittest

import zope
from nti.dataserver.tests.mock_dataserver import DataserverTestLayer
from nti.dataserver.tests.mock_dataserver import _TestBaseMixin
from nti.testing.layers import find_test


class AuthenticationTestLayer(DataserverTestLayer):
    set_up_packages = ('nti.dataserver', 'nti.app.authentication', )

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        pass

    @classmethod
    def testSetUp(cls, test=None):
        test = test or find_test()
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass


class AuthenticationLayerTest(_TestBaseMixin,
                              unittest.TestCase):
    layer = AuthenticationTestLayer
