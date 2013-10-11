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


from hamcrest import assert_that
from hamcrest import contains
from hamcrest import has_property
from nti.testing.matchers import validly_provides
from zope.component.hooks import getSite, setSite
from .mock_dataserver import SharedConfiguringTestBase

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

class TestSiteSubscriber(SharedConfiguringTestBase):


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
