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
import nti.tests
from nti.tests import  verifiably_provides
import fudge

from zope import interface
from zope import component
from zope.component.hooks import site


from nti.dataserver.site import _TrivialSite
from nti.appserver.sites import MATHCOUNTS
from nti.externalization.externalization import to_external_object

from ..interfaces import IContentPackageLibrary
from ..interfaces import IFilesystemContentPackageLibrary
from ..interfaces import IAbsoluteContentUnitHrefMapper
from ..interfaces import IS3Key
from ..filesystem import EnumerateOnceFilesystemLibrary
from ..boto_s3 import BotoS3BucketContentLibrary

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
			component="nti.appserver.sites.MATHCOUNTS"
			provides="zope.component.interfaces.IComponents"
			name="mathcounts.nextthought.com" />

		<registerIn registry="nti.appserver.sites.MATHCOUNTS">
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

class TestZcml(nti.tests.ConfiguringTestBase):


	def test_filesystem_site_registrations(self):
		"Can we add new registrations in a sub-site?"

		self.configure_packages( ('nti.contentlibrary', 'nti.externalization') )
		self.configure_string( ZCML_STRING )
		assert_that( MATHCOUNTS.__bases__, is_( (component.globalSiteManager,) ) )

		assert_that( component.queryUtility( IContentPackageLibrary ), is_( none() ) )

		with site( _TrivialSite( MATHCOUNTS ) ):
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

		fake_conn = fake_connect.expects_call().returns_fake()
		fake_bucket = fake_conn.expects( 'get_bucket' ).returns_fake()
		fake_bucket.expects('list').returns( [] )

		self.configure_string( BOTO_ZCML_STRING )
		assert_that( component.queryUtility( IContentPackageLibrary ), is_( none() ) )

		with site( _TrivialSite( MATHCOUNTS ) ):
			lib = component.getUtility( IContentPackageLibrary )
			assert_that( lib, verifiably_provides( IContentPackageLibrary ) )
			assert_that( lib, is_( BotoS3BucketContentLibrary ) )

			@interface.implementer(IS3Key)
			class Key(object):
				bucket = None
				key = 'my.key'

			mapper = component.getAdapter( Key(), IAbsoluteContentUnitHrefMapper )
			assert_that( mapper, has_property( 'href', '//cdnname/my.key' ) )
