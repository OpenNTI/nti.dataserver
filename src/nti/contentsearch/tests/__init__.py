#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.testing.layers import find_test
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

import zope.testing.cleanup

phrases = (u"Yellow brown",
           u"Blue red green render purple?",
           u"Alpha beta",
           u"Gamma delta epsilon omega.",
           u"One two",
           u"Three rendered four five.",
           u"Quick went",
           u"Every red town.",
           u"Yellow uptown",
           u"Interest rendering outer photo!",
           u"Preserving extreme",
           u"Chicken hacker")

domain = (u"alfa", u"bravo", u"charlie", u"delta", u"echo", u"foxtrot",
          u"golf", u"hotel", u"india", u"juliet", u"kilo", u"lima", u"mike",
          u"november", u"oscar", u"papa", u"quebec", u"romeo", u"sierra",
          u"tango", u"uniform", u"victor", u"whiskey", u"xray", u"yankee",
          u"zulu")

zanpakuto_commands = (u"Shoot To Kill",
                      u"Bloom, Split and Deviate",
                      u"Rankle the Seas and the Skies",
                      u"Lightning Flash Flame Shell",
                      u"Flower Wind Rage and Flower God Roar, Heavenly Wind Rage and Heavenly Demon Sneer",
                      u"All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade",
                      u"Cry, Raise Your Head, Rain Without end",
                      u"Sting All Enemies To Death",
                      u"Reduce All Creation to Ash",
                      u"Sit Upon the Frozen Heavens",
                      u"Call forth the Twilight",
                      u"Multiplication and subtraction of fire and ice, show your might")


class SharedConfiguringTestLayer(ZopeComponentLayer,
                                 ConfiguringLayerMixin,
                                 DSInjectorMixin):

    set_up_packages = ('nti.dataserver', 'nti.contentsearch')

    @classmethod
    def setUp(cls):
        cls.setUpPackages()

    @classmethod
    def tearDown(cls):
        cls.tearDownPackages()
        zope.testing.cleanup.cleanUp()

    @classmethod
    def testSetUp(cls, test=None):
        cls.setUpTestDS(test)

    @classmethod
    def testTearDown(cls):
        pass
