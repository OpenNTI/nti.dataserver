#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import tempfile
import shutil

from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin
from zope.component.hooks import setHooks

from zope import component
import zope.testing.cleanup

from ..interfaces import IContentUnitAnnotationUtility

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

class ContentlibraryTestLayer(ZopeComponentLayer,
							  ConfiguringLayerMixin,
							  DSInjectorMixin):


	set_up_packages = ('nti.contentlibrary','nti.externalization', 'nti.contenttypes.presentation', 'nti.dataserver', 'nti.app.contentlibrary')

	@classmethod
	def setUp(cls):
		setHooks() # in case something already tore this down
		cls.setUpPackages()
		cls.old_data_dir = os.getenv('DATASERVER_DATA_DIR')
		cls.new_data_dir = tempfile.mkdtemp(dir="/tmp")
		os.environ['DATASERVER_DATA_DIR'] = cls.new_data_dir

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
		cls.setUpTestDS(test)
		shutil.rmtree(cls.new_data_dir, True)
		os.environ['DATASERVER_DATA_DIR'] = cls.old_data_dir or '/tmp'

	@classmethod
	def testTearDown(cls):
		pass


import unittest
from nti.testing.base import AbstractTestBase

class ContentlibraryLayerTest(unittest.TestCase):
	layer = ContentlibraryTestLayer

	get_configuration_package = AbstractTestBase.get_configuration_package.__func__
