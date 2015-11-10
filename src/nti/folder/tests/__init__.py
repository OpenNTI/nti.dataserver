#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.testing.layers import find_test
from nti.testing.layers import GCLayerMixin
from nti.testing.layers import ZopeComponentLayer
from nti.testing.layers import ConfiguringLayerMixin

from nti.dataserver.tests.mock_dataserver import DSInjectorMixin

import zope.testing.cleanup

class SharedConfiguringTestLayer(ZopeComponentLayer,
								 GCLayerMixin,
								 ConfiguringLayerMixin,
								 DSInjectorMixin):

	set_up_packages = ('nti.folder',)

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

class DummyObject(object):

	def __init__(self, uid):
		self.id = uid

	def __of__(self, obj):
		return self

	def dummy_method(self):
		return self.id

from zope.interface import implementer

from nti.folder.interfaces import IOrderable

@implementer(IOrderable)
class Orderable(DummyObject):
	"""
	orderable mock object 
	"""

class Chaoticle(DummyObject):
	""" 
	non-orderable mock object;  this does not implement `IOrderable` 
	"""
