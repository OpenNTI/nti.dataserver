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
from hamcrest import has_length
from hamcrest import is_not as does_not
from hamcrest import not_none
from hamcrest import is_
from hamcrest import same_instance

from nti.testing.matchers import validly_provides
from zope import component
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


# Match a hierarchy we have in nti.app.sites.demo:
# global
#  \
#   eval
#   |\
#   | eval-alpha
#   \
#    demo
#     \
#      demo-alpha

EVAL = BaseComponents(BASE,
					  name='eval.nextthoughttest.com',
					  bases=(BASE,))

EVALALPHA = BaseComponents(EVAL,
						   name='eval-alpha.nextthoughttest.com',
						   bases=(EVAL,))

DEMO = BaseComponents(EVAL,
					  name='demo.nextthoughttest.com',
					  bases=(EVAL,))

DEMOALPHA = BaseComponents(DEMO,
						   name='demo-alpha.nextthoughttest.com',
						   bases=(DEMO,))

_SITES = (EVAL, EVALALPHA, DEMO, DEMOALPHA)


from zope.component.interfaces import IComponents

from .mock_dataserver import DataserverLayerTest
from .mock_dataserver import mock_db_trans

from .mock_dataserver import WithMockDS

from nti.testing.matchers import verifiably_provides
from zope.component.interfaces import ISite
from zope.site.interfaces import INewLocalSite
from ..interfaces import IHostPolicySiteManager

from ..site import get_site_for_site_names
from ..site import synchronize_host_policies
from ..site import _find_site_components
from ..site import run_job_in_all_host_sites

class ITestSiteSync(interface.Interface):
	pass

@interface.implementer(ITestSiteSync)
class ASync(object):
	pass

@interface.implementer(ITestSiteSync)
class OtherSync(object):
	pass


class TestSiteSync(DataserverLayerTest):

	_events = ()

	def setUp(self):
		super(TestSiteSync,self).setUp()
		for site in _SITES:
			# See explanation in nti.appserver.policies.sites; in short,
			# the teardown process can disconnect the resolution order of
			# these objects, and since they don't descend from the bases declared
			# in that module, they fail to get reset.
			site.__init__( site.__parent__, name=site.__name__, bases=site.__bases__ )
			BASE.registerUtility(site, name=site.__name__, provided=IComponents)
		BASE.registerHandler(self._on_host_site, required=(IHostPolicySiteManager, INewLocalSite))
		DEMO.registerUtility(ASync(), provided=ITestSiteSync)
		self._events = []

	def tearDown(self):
		for site in _SITES:
			BASE.unregisterUtility(site, name=site.__name__, provided=IComponents)
		BASE.unregisterHandler(self._on_host_site, required=(IHostPolicySiteManager, INewLocalSite))
		super(TestSiteSync,self).tearDown()

	def _on_host_site(self, *args):
		self._events.append( args )


	def test_simple_ro(self):
		# Check that resolution order is what we think. See
		# site.py
		# This simulates the layout in the database and global
		# site manager.
		class GSM(object): pass
		# DB
		class Root(GSM): pass
		class DS(Root): pass
		# global sites
		class Base(GSM): pass
		class S1(Base): pass
		class S2(Base): pass

		# DB sites
		class PS1(S1, DS): pass
		class PS2(S2, PS1): pass


		assert_that( ro.ro(PS2),
					 is_( [PS2, S2, PS1, S1, Base, DS, Root, GSM, object] ) )

	@WithMockDS
	def test_site_sync(self):

		for site in _SITES:
			assert_that( _find_site_components( (site.__name__,)),
						 is_( not_none() ))

		with mock_db_trans(self.ds) as conn:
			for site in _SITES:
				assert_that( _find_site_components( (site.__name__,)),
							 is_( not_none() ))


			ds = conn.root()['nti.dataserver']
			assert ds is not None
			sites = ds['++etc++hostsites']
			for site in _SITES:
				assert_that( sites, does_not(has_key(site.__name__)))

			synchronize_host_policies()
			synchronize_host_policies()

			assert_that( self._events, has_length(len(_SITES)) )
			# These were put in in order
			#assert_that( self._events[0][0].__parent__,
			#			 has_property('__name__', EVAL.__name__))

		with mock_db_trans(self.ds) as conn:
			for site in _SITES:
				assert_that( _find_site_components( (site.__name__,)),
							 is_( not_none() ))

			ds = conn.root()['nti.dataserver']

			assert ds is not None
			sites = ds['++etc++hostsites']

			assert_that( sites, has_key(EVAL.__name__))
			assert_that( sites[EVAL.__name__], verifiably_provides(ISite) )



			# If we ask the demoalpha persistent site for an ITestSyteSync,
			# it will find us, because it goes to the demo global site
			assert_that( sites[DEMOALPHA.__name__].getSiteManager().queryUtility(ITestSiteSync),
						 is_(ASync))

			# However, if we put something in the demo *persistent* site, it
			# will find that
			sites[DEMO.__name__].getSiteManager().registerUtility(OtherSync())
			assert_that( sites[DEMOALPHA.__name__].getSiteManager().queryUtility(ITestSiteSync),
						 is_(OtherSync))

			# Verify the resolution order too
			def _name(x):
				if x.__name__ == '++etc++site':
					return 'P' + str(x.__parent__.__name__)
				return x.__name__
			assert_that([_name(x) for x in ro.ro(sites[DEMOALPHA.__name__].getSiteManager())],
						 is_([u'Pdemo-alpha.nextthoughttest.com',
							  u'demo-alpha.nextthoughttest.com',
							  u'Pdemo.nextthoughttest.com',
							  u'demo.nextthoughttest.com',
							  u'Peval.nextthoughttest.com',
							  u'eval.nextthoughttest.com',
							  u'Pdataserver2',
							  u'PNone',
							  'base']))

			# including if we ask to travers from top to bottom
			names = list()
			def func():
				names.append(_name(component.getSiteManager()))

			run_job_in_all_host_sites(func)
			# Note that PDemo and Peval-alpha are arbitrary, they both
			# descend from eval; however, we maintain alphabetical order,
			# which is nice
			assert_that( names, is_([u'Peval.nextthoughttest.com',
									 u'Pdemo.nextthoughttest.com',
									 u'Peval-alpha.nextthoughttest.com',
									 u'Pdemo-alpha.nextthoughttest.com']))


			# And that it's what we get back if we ask for it
			assert_that( get_site_for_site_names( (DEMOALPHA.__name__,)),
						 is_( same_instance( sites[DEMOALPHA.__name__]) ) )

		# No new sites created
		assert_that( self._events, has_length(len(_SITES)) )
