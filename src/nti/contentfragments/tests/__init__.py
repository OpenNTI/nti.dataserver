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
from nti.testing.layers import find_test

import zope.testing.cleanup

class ContentfragmentsTestLayer(ZopeComponentLayer,
								ConfiguringLayerMixin):


	set_up_packages = ('nti.contentfragments','nti.contentprocessing')

	@classmethod
	def setUp(cls):
		cls.setUpPackages()

	@classmethod
	def tearDown(cls):
		cls.tearDownPackages()
		zope.testing.cleanup.cleanUp()

	@classmethod
	def testSetUp(cls, test=None):
		pass

	@classmethod
	def testTearDown(cls):
		pass


import unittest
class ContentfragmentsLayerTest(unittest.TestCase):
	layer = ContentfragmentsTestLayer
