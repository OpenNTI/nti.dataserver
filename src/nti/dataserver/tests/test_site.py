#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import contains
from hamcrest import has_property
from hamcrest import has_key
from hamcrest import is_not as does_not
from hamcrest import not_none
from hamcrest import is_
from nti.testing.matchers import validly_provides
from zope.component.hooks import getSite, setSite
from .mock_dataserver import SharedConfiguringTestLayer

from zope.interface import Interface
from zope import interface
from zope.interface import ro

class IMock(Interface):
	pass

@interface.implementer(IMock)
class MockSite(object):

	__parent__ = None
	__name__ = None
	def __init__( self, site_man=None):
		self.site_man = site_man

	def getSiteManager(self):
		return self.site_man

from ..site import threadSiteSubscriber
from ..site import _HostSiteManager as HSM
from z3c.baseregistry.baseregistry import BaseComponents
from zope.component import globalSiteManager as BASE

class IFoo(Interface):
	pass

class TestSiteSubscriber(unittest.TestCase):

	layer = SharedConfiguringTestLayer


	def testProxyHostComps(self):
		pers_comps = BaseComponents(BASE, 'persistent', (BASE,) )
		host_comps = BaseComponents(BASE, 'example.com', (BASE,) )
		host_sm = HSM( 'example.com', 'siteman', host_comps, pers_comps )
		host_site = MockSite(host_sm)
		host_site.__name__ = host_sm.__name__
		setSite( host_site )

		new_comps = BaseComponents(BASE, 'sub_site', (pers_comps,) )
		new_site = MockSite(new_comps)
		new_site.__name__ = new_comps.__name__
		interface.alsoProvides( new_site, IFoo )

		threadSiteSubscriber( new_site, None )

		cur_site = getSite()
		# It should implement the static and dynamic
		# ifaces
		assert_that( cur_site, validly_provides(IFoo) )
		assert_that( cur_site, validly_provides(IMock) )

		# It should have the marker property
		assert_that( cur_site.getSiteManager(),
					 has_property( '_host_components',
								   host_comps ) )

		assert_that( ro.ro( cur_site.getSiteManager() ),
					 contains(
						 # The first entry is synthesized
						 has_property( '__name__', new_comps.__name__),
						 pers_comps,
						 # The host comps appear after all the bases
						 # in the ro of the new site
						 host_comps,
						 BASE ) )

SITE_NAME = 'test_site.nextthought.com'
SITE_ZCML_STRING = """
		<configure xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:lib="http://nextthought.com/ntp/contentlibrary"
			i18n_domain='nti.dataserver'>

		<include package="zope.component" />
		<include package="zope.annotation" />
		<include package="z3c.baseregistry" file="meta.zcml" />


		<utility
			component="nti.appserver.policies.sites.BASECOPPA"
			provides="zope.component.interfaces.IComponents"
			name="test_site.nextthought.com" />
		</configure>"""

from zope.configuration import xmlconfig, config

from .mock_dataserver import DataserverLayerTest
from .mock_dataserver import mock_db_trans

from .mock_dataserver import WithMockDS

from nti.testing.matchers import verifiably_provides
from zope.component.interfaces import ISite


from ..site import synchronize_host_policies
from ..site import _find_site_components

class TestSiteSync(DataserverLayerTest):


	def setUp(self):
		super(TestSiteSync,self).setUp()
		# We must do this outside of the context of a
		# WithMockDS decorator, because that decorator interjects
		# a local site manager, but for the hierarchy to be correct
		# we need this to be in the GSM
		context = config.ConfigurationMachine()

		xmlconfig.registerCommonDirectives( context )

		xmlconfig.string( SITE_ZCML_STRING, context )

	@WithMockDS
	def test_site_sync(self):

		assert_that( _find_site_components( (SITE_NAME,)),
					 is_( not_none() ))

		with mock_db_trans(self.ds) as conn:

			assert_that( _find_site_components( (SITE_NAME,)),
					 is_( not_none() ))

			ds = conn.root()['nti.dataserver']
			assert ds is not None
			sites = ds['++etc++hostsites']
			assert_that( sites, does_not(has_key(SITE_NAME)))

			synchronize_host_policies()

		with mock_db_trans(self.ds) as conn:
			ds = conn.root()['nti.dataserver']

			assert ds is not None
			sites = ds['++etc++hostsites']
			assert_that( sites, has_key(SITE_NAME))
			assert_that( sites[SITE_NAME], verifiably_provides(ISite) )
