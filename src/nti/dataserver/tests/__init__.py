#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import zope.testing.cleanup

from zope.component.hooks import setHooks

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin


from nti.testing.layers import ConfiguringLayerMixin
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.zodb import ZODBLayer

__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


# for export
from nti.testing import matchers
has_attr = matchers.has_attr
provides = matchers.provides
implements = matchers.implements


class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 GCLayerMixin,
                                 ConfiguringLayerMixin,
                                 DSInjectorMixin):

    set_up_packages = ('nti.dataserver',)

    @classmethod
    def db(cls):
        return ZODBLayer.db

    @classmethod
    def setUp(cls):
        setHooks()
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None): # pylint:disable=arguments-differ
        setHooks()
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass
