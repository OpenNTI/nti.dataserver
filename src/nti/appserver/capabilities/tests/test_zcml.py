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
from hamcrest import none
from hamcrest import is_not
does_not = is_not
from hamcrest import has_property
from hamcrest import has_entry
from hamcrest import is_in

import nti.tests

from zope import component
from zope.component.hooks import site
from zope.schema import vocabulary

from ..interfaces import ICapability, VOCAB_NAME
from ..vocabulary import CapabilityNameTokenVocabulary, CapabilityUtilityVocabulary, CapabilityNameVocabulary

class TestZcml(nti.tests.ConfiguringTestBase):

	def test_default_registrations(self):
		self.configure_packages( set_up_packages=( ('capabilities.zcml', 'nti.appserver.capabilities',), ) )
		self._check_cap_present()

	def _check_cap_present( self, cap_name='nti.platform.p2p.chat' ):
		component.getUtility( ICapability, cap_name )

		assert_that( cap_name, is_in( CapabilityNameTokenVocabulary() ) )
		assert_that( cap_name, is_in( CapabilityNameVocabulary(None) ) )

		assert_that( CapabilityUtilityVocabulary( None ).getTermByToken(cap_name), has_property( 'token', cap_name ) )

	def test_site_registrations(self):
		"Can we add new registrations in a sub-site?"
		from nti.appserver import sites
		self.configure_packages( set_up_packages=('nti.appserver.capabilities',) )
		zcml_string = """
		<configure xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:cap="http://nextthought.com/ntp/capabilities"
			i18n_domain='nti.dataserver'>

		<include package="zope.component" />
		<include package="z3c.baseregistry" file="meta.zcml" />

		<utility
			component="nti.appserver.sites.MATHCOUNTS"
			provides="zope.component.interfaces.IComponents"
			name="mathcounts.nextthought.com" />

		<registerIn registry="nti.appserver.sites.MATHCOUNTS">
			<cap:capability
			id='nti.only_in_mathcounts'
			title="only_in_mathcounts"/>
		</registerIn>
		</configure>
		"""
		self.configure_string( zcml_string )
		self._check_cap_present() # the defaults are there
		from nti.dataserver.site import _TrivialSite
		from nti.appserver.sites import MATHCOUNTS

		# First, it's not present globally, in any utility
		cap_name = 'nti.only_in_mathcounts'

		assert_that( component.queryUtility( ICapability, cap_name ), is_( none() ) )

		assert_that( cap_name, is_not( is_in( CapabilityNameTokenVocabulary() ) ) )
		assert_that( cap_name, is_not( is_in( CapabilityNameVocabulary(None) ) ) )
		assert_that( cap_name, is_not( is_in( vocabulary.getVocabularyRegistry().get( None, VOCAB_NAME ) ) ) )

		# Now, in the sub site, they are bath present
		with site( _TrivialSite( MATHCOUNTS ) ):
			self._check_cap_present( )
			self._check_cap_present( cap_name )
