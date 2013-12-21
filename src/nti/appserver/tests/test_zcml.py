#!/Sr/bin/env python
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
from hamcrest import has_item
from hamcrest import is_
from hamcrest import is_not
does_not = is_not

import nti.testing.base

from zope import component

from zope.component.hooks import site

from nti.dataserver.site import _TrivialSite
from nti.appserver.policies.sites import BASECOPPA as MATHCOUNTS

from ..interfaces import ILogonWhitelist

ZCML_STRING = """
		<configure xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:logon="http://nextthought.com/ntp/logon"
			i18n_domain='nti.dataserver'>

		<include package="zope.component" />
		<include package="zope.annotation" />
		<include package="z3c.baseregistry" file="meta.zcml" />
		<include package="." file="meta.zcml" />

		<utility
			component="nti.appserver.policies.sites.BASECOPPA"
			provides="zope.component.interfaces.IComponents"
			name="mathcounts.nextthought.com" />

		<registerIn registry="nti.appserver.policies.sites.BASECOPPA">
			<logon:whitelist
				entities="a b c" />
		</registerIn>
		</configure>
		"""

class TestZcml(nti.testing.base.ConfiguringTestBase):

	def test_site_registrations(self):
		self.configure_string( ZCML_STRING )
		assert_that( MATHCOUNTS.__bases__, is_( (component.globalSiteManager,) ) )
		with site( _TrivialSite( MATHCOUNTS ) ):
			whitelist = component.getUtility(ILogonWhitelist)

			assert_that( whitelist, has_item('a'))
			assert_that( whitelist, has_item('b'))
			assert_that( whitelist, has_item('c'))
			assert_that( whitelist, does_not(has_item('d')))
