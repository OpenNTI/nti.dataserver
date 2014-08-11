#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin
from zope.component.hooks import setHooks

import zope.testing.cleanup

from ..interfaces import IContentUnitAnnotationUtility
from zope import component

class ContentlibraryTestLayer(ZopeComponentLayer,
							  ConfiguringLayerMixin):


	set_up_packages = ('nti.contentlibrary','nti.externalization')

	@classmethod
	def setUp(cls):
		setHooks() # in case something already tore this down
		cls.setUpPackages()

	@classmethod
	def tearDown(cls):
		cls.tearDownPackages()
		zope.testing.cleanup.cleanUp()

	@classmethod
	def testSetUp(cls, test=None):
		# If we installed any annotations, clear them, since
		# they are tracked by NTIID and would otherwise persist
		annotations = component.getUtility(IContentUnitAnnotationUtility)
		annotations.annotations.clear()

	@classmethod
	def testTearDown(cls):
		pass


import unittest
from nti.testing.base import AbstractTestBase

class ContentlibraryLayerTest(unittest.TestCase):
	layer = ContentlibraryTestLayer

	get_configuration_package = AbstractTestBase.get_configuration_package.__func__
