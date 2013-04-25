#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from zope import component
from zope.component.hooks import site

from nti.appserver.sites import MATHCOUNTS
from nti.dataserver.site import _TrivialSite

from ..interfaces import IPurchasable

import nti.tests
from nti.tests import  verifiably_provides

from hamcrest import (assert_that, is_, none, has_property)

HEAD_ZCML_STRING = """
		<configure xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:pcs="http://nextthought.com/ntp/purchasable"
			i18n_domain='nti.dataserver'>

		<include package="zope.component" />
		<include package="zope.annotation" />
		<include package="z3c.baseregistry" file="meta.zcml" />
		<include package="." file="meta.zcml" />

		<utility
			component="nti.appserver.sites.MATHCOUNTS"
			provides="zope.component.interfaces.IComponents"
			name="mathcounts.nextthought.com" />

		<registerIn registry="nti.appserver.sites.MATHCOUNTS">
"""

ZCML_STRING = HEAD_ZCML_STRING + """
	<pcs:registerPurchasable
		ntiid="tag:nextthought.com,2011-10:PRMIA-purchasable-RiskCourse"
		title="NextThought Help Center"
		provider="NTI-TEST"
		author="NEXTTHOUGHT"
		amount="100"
		currency="USD"
		discountable="False"
		bulk_purchase="True"
		items="tag:nextthought.com,2011-10:PRMIA-HTML-PRMIA_RiskCourse.advanced_stress_testing_for_financial_institutions">

		also here is some text
		&amp; some more text
		<![CDATA[
		<p>html paragraph</p>
		<div class='foo'>html div</div>
		]]>
	</pcs:registerPurchasable>
</registerIn>
</configure>
"""

class TestZcml(nti.tests.ConfiguringTestBase):

	def test_site_registration_and_complex_description(self):

		self.configure_packages(('nti.contentfragments',))
		self.configure_string(ZCML_STRING)
		assert_that(MATHCOUNTS.__bases__, is_((component.globalSiteManager,)))

		assert_that(component.queryUtility(IPurchasable, name="tag:nextthought.com,2011-10:PRMIA-purchasable-RiskCourse"), is_(none()))

		with site(_TrivialSite(MATHCOUNTS)):
			pur = component.getUtility(IPurchasable, name="tag:nextthought.com,2011-10:PRMIA-purchasable-RiskCourse")
			assert_that(pur, verifiably_provides(IPurchasable))
			assert_that(pur, has_property('Description',
											"also here is some text\n\t\t& some more text\n\t\t\n\t\t<p>html paragraph</p>\n\t\t<div class='foo'>html div</div>"))
