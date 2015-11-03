#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
does_not = is_not

import fudge

from zope import interface
from zope import component
from zope.component.hooks import site

from nti.appserver.policies.sites import BASECOPPA  #TODO: Remove this

from nti.contentlibrary.interfaces import IS3Key
from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IAbsoluteContentUnitHrefMapper
from nti.contentlibrary.interfaces import IFilesystemContentPackageLibrary

from nti.contentlibrary.boto_s3 import BotoS3BucketContentLibrary

from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary

from nti.externalization.externalization import to_external_object

from nti.site.transient import TrivialSite

from nti.testing.matchers import verifiably_provides

HEAD_ZCML_STRING = """
		<configure xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:lib="http://nextthought.com/ntp/contentlibrary"
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
"""

ZCML_STRING = HEAD_ZCML_STRING + """
			<lib:filesystemLibrary
				directory="tests/"
				prefix="SomePrefix"
				/>
		</registerIn>
		</configure>
		"""

BOTO_ZCML_STRING = HEAD_ZCML_STRING + """
			<lib:s3Library
				bucket="foobar"
				cdn_name="cdnname"
				/>
		</registerIn>
		</configure>
		"""

from zope.configuration import xmlconfig, config

from nti.contentlibrary.tests import ContentlibraryLayerTest

class TestZcml(ContentlibraryLayerTest):

	def setUp(self):
		super(TestZcml,self).setUp()
		xsite = BASECOPPA
		xsite.__init__( xsite.__parent__, name=xsite.__name__, bases=xsite.__bases__ )

	def test_filesystem_site_registrations(self):
		#"Can we add new registrations in a sub-site?"

		context = config.ConfigurationMachine()
		context.package = self.get_configuration_package()
		xmlconfig.registerCommonDirectives( context )

		xmlconfig.string( ZCML_STRING, context )

		assert_that( BASECOPPA.__bases__, is_( (component.globalSiteManager,) ) )

		# assert_that( component.queryUtility( IContentPackageLibrary ), is_( none() ) )

		with site( TrivialSite( BASECOPPA ) ):
			lib = component.getUtility( IContentPackageLibrary )
			assert_that( lib, verifiably_provides( IFilesystemContentPackageLibrary ) )
			assert_that( lib, is_( EnumerateOnceFilesystemLibrary ) )
			# Did the right prefix come in?
			assert_that( lib, has_property( 'url_prefix', '/SomePrefix/' ) )
			pack_ext = to_external_object( lib[0] )
			assert_that( pack_ext, has_entry( 'href', '/SomePrefix/TestFilesystem/index.html' ) )
			assert_that( pack_ext, has_entry( 'root', '/SomePrefix/TestFilesystem/' ) )


	@fudge.patch('boto.connect_s3')
	def test_register_boto(self, fake_connect):
		#"Can we add new boto registrations in a sub-site?"
		fake_conn = fake_connect.expects_call().returns_fake()
		fake_bucket = fake_conn.expects( 'get_bucket' ).returns_fake()
		fake_bucket.expects('list').returns( [] )

		context = config.ConfigurationMachine()
		context.package = self.get_configuration_package()
		xmlconfig.registerCommonDirectives( context )

		xmlconfig.string( BOTO_ZCML_STRING, context )
		# assert_that( component.queryUtility( IContentPackageLibrary ), is_( none() ) )

		with site( TrivialSite( BASECOPPA ) ):
			lib = component.getUtility( IContentPackageLibrary )
			assert_that( lib, verifiably_provides( IContentPackageLibrary ) )
			assert_that( lib, is_( BotoS3BucketContentLibrary ) )

			@interface.implementer(IS3Key)
			class Key(object):
				bucket = None
				key = 'my.key'

			mapper = component.getAdapter( Key(), IAbsoluteContentUnitHrefMapper )
			assert_that( mapper, has_property( 'href', '//cdnname/my.key' ) )
