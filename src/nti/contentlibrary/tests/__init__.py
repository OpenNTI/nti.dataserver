#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import shutil
import tempfile

from zope.component.hooks import setHooks

from zope import component

import zope.testing.cleanup

from nti.contentlibrary.interfaces import IContentUnitAnnotationUtility

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

class ContentlibraryTestLayer(ZopeComponentLayer,
							  ConfiguringLayerMixin,
							  DSInjectorMixin):


	set_up_packages = (	'nti.contentlibrary', 
						'nti.externalization', 
						'nti.contenttypes.presentation', 
						'nti.dataserver')

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
