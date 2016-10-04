#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import shutil
import tempfile

from nti.app.testing.application_webtest import ApplicationTestLayer

class SAMLTestLayer(ApplicationTestLayer):

	set_up_packages = ('nti.app.saml.tests',)

	@classmethod
	def setUp(cls):
		cls.setUpPackages()

	@classmethod
	def tearDown(cls):
		pass

	@classmethod
	def testSetUp(cls):
		pass

	@classmethod
	def testTearDown(cls):
		pass
