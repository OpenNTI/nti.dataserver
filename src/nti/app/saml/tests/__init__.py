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
		# We need to use configure_packages instead of setUpPackages
		# to avoid having zope.eventtesting.events.append duplicated
		# as a handler. This is poorly documented in nti.testing 1.0.0.
		# Passing in our context is critical.
		cls.configure_packages(set_up_packages=cls.set_up_packages,
                               features=cls.features,
                               context=cls.configuration_context)


	@classmethod
	def tearDown(cls):
		pass

	@classmethod
	def testSetUp(cls):
		pass

	@classmethod
	def testTearDown(cls):
		pass
