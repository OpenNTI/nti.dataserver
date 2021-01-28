#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import zope

from nti.dataserver.tests.mock_dataserver import DataserverTestLayer

from nti.testing.layers import find_test


class PoliciesTestLayer(DataserverTestLayer):

    set_up_packages = ('nti.dataserver', 'nti.appserver.policies')

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        test = test or find_test()
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass
