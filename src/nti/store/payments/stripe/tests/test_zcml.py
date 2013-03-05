#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from zope import component

from .. import interfaces as stripe_interfaces

from . import ConfiguringTestBase

class TestZcml(ConfiguringTestBase):

	def test_default_registrations(self):

		cap_name = 'NTI-TEST'
		component.getUtility( stripe_interfaces.IStripeAccessKey, cap_name )
