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
from nose.tools import assert_raises

import nti.tests
from nti.tests import is_empty

from zope import component
from zope.contentprovider.interfaces import IContentProvider
from zope.component.hooks import site


from nti.dataserver.site import _TrivialSite
from nti.appserver.sites import MATHCOUNTS



ZCML_STRING = """
		<configure xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:cp="http://nextthought.com/ntp/contentproviders"
			i18n_domain='nti.dataserver'>

		<include package="zope.component" />
		<include package="zope.annotation" />
		<include package="z3c.baseregistry" file="meta.zcml" />
		<include package="." file="meta.zcml" />

		<utility
			component="nti.appserver.sites.MATHCOUNTS"
			provides="zope.component.interfaces.IComponents"
			name="mathcounts.nextthought.com" />

			<cp:pyramidTemplate
				name='foo.bar'
				for='* * *'
				template='nti.appserver:templates/failed_username_recovery_email.txt'
				/>


		<registerIn registry="nti.appserver.sites.MATHCOUNTS">
			<cp:pyramidTemplate
				name='foo.bar'
				for='* * *'
				template='nti.appserver:templates/failed_username_recovery_email.pt'
				/>
		</registerIn>
		</configure>
		"""

class TestZcml(nti.tests.ConfiguringTestBase):



	def test_site_registrations(self):
		"Can we add new registrations in a sub-site?"

		self.configure_string( ZCML_STRING )
		assert_that( MATHCOUNTS.__bases__, is_( (component.globalSiteManager,) ) )

		top = component.getMultiAdapter( (None,None,None),
										 IContentProvider,
										 name='foo.bar' )
		assert_that( top, has_property( '__name__', 'nti.appserver:templates/failed_username_recovery_email.txt' ) )

		with site( _TrivialSite( MATHCOUNTS ) ):
			sub = component.getMultiAdapter( (None,None,None),
											 IContentProvider,
											 name='foo.bar' )
			assert_that( sub, has_property( '__name__', 'nti.appserver:templates/failed_username_recovery_email.pt' ) )
