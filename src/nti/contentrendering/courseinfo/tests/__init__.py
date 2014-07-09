#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

import zope.testing.cleanup

from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

class SharedConfiguringTestLayer(ZopeComponentLayer,
								 ConfiguringLayerMixin):

	set_up_packages = ('nti.contentrendering', 'nti.contentrendering.courseinfo')

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

class CourseinfoLayerTest(unittest.TestCase):
	layer = SharedConfiguringTestLayer
