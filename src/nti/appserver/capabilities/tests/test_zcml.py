#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_property
from hamcrest import has_entry
from hamcrest import is_in

import nti.tests

from zope import component

from ..interfaces import ICapability
from ..vocabulary import CapabilityNameTokenVocabulary, CapabilityUtilityVocabulary, CapabilityNameVocabulary

class TestZcml(nti.tests.ConfiguringTestBase):

	def test_default_registrations(self):
		# TODO: This is a pretty poor test
		self.configure_packages( set_up_packages=( ('capabilities.zcml', 'nti.appserver.capabilities',), ) )

		cap_name = 'nti.platform.p2p.chat'
		component.getUtility( ICapability, cap_name )

		assert_that( cap_name, is_in( CapabilityNameTokenVocabulary() ) )
		assert_that( cap_name, is_in( CapabilityNameVocabulary(None) ) )

		assert_that( CapabilityUtilityVocabulary( None ).getTermByToken(cap_name), has_property( 'token', cap_name ) )
