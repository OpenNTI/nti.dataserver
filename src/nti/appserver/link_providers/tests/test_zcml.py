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
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import is_in
from nose.tools import assert_raises

import nti.tests
from nti.tests import is_empty

from zope import component
from zope import interface
from zope.component.hooks import site
from zope.configuration.exceptions import ConfigurationError

from nti.dataserver.site import _TrivialSite
from nti.appserver.sites import MATHCOUNTS


from nti.dataserver import interfaces as nti_interfaces
from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from nti.dataserver import users
from pyramid.request import Request

ZCML_STRING = """
		<configure xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:link="http://nextthought.com/ntp/link_providers"
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
			<link:userLink
				name='foo.bar'
				minGeneration='1234'
				url='/relative/path'
				for='nti.dataserver.interfaces.ICoppaUser' />
		</registerIn>
		</configure>
		"""

class TestZcml(nti.tests.ConfiguringTestBase):



	def test_site_registrations(self):
		"Can we add new registrations in a sub-site?"

		self.configure_string( ZCML_STRING )
		assert_that( MATHCOUNTS.__bases__, is_( (component.globalSiteManager,) ) )
		with site( _TrivialSite( MATHCOUNTS ) ):
			user = users.User( 'foo@bar' )
			request = Request.blank( '/' )
			# Nothing until we provide ICoppaUser
			assert_that( list( component.subscribers( (user, request), IAuthenticatedUserLinkProvider) ), is_empty() )

			interface.alsoProvides( user, nti_interfaces.ICoppaUser )

			providers = list( component.subscribers( (user, request), IAuthenticatedUserLinkProvider ) )
			assert_that( providers, has_length( 1 ) )

			# Make sure all our properties got where we wanted them
			provider = providers[0]
			assert_that( provider.url, is_( '/relative/path' ) )
			assert_that( provider.minGeneration, is_( '1234' ) )

			assert_that( provider.get_links( ), has_length( 1 ) )
			assert_that( provider.get_links()[0].elements[-1], is_( 'foo.bar' ) )

			provider.delete_link( provider.__name__ )

			assert_that( provider.get_links( ), is_empty() )

	def test_raises(self):
		from ..zcml import registerUserLink

		context = object()
		with assert_raises(ConfigurationError):
			registerUserLink( context, name="name", named="named" )
		with assert_raises(ConfigurationError):
			registerUserLink( context, name='' )

		with assert_raises(ConfigurationError):
			registerUserLink( context, name='link', for_=None )

		with assert_raises(ConfigurationError):
			registerUserLink( context, name='link', field='abc', url='def' )
		with assert_raises(ConfigurationError):
			registerUserLink( context, name='link', field='abc', minGeneration='def' )
		with assert_raises(ConfigurationError):
			registerUserLink( context, name='link', field='abc', view_named='def' )
