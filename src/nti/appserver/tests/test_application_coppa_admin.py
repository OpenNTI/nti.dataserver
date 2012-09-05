#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property
from hamcrest import greater_than_or_equal_to
from hamcrest import is_not as does_not
from nti.tests import verifiably_provides
from zope import interface

from webtest import TestApp

import os.path

import urllib

from nti.ntiids import ntiids
from nti.externalization.oids import to_external_ntiid_oid
from nti.dataserver import contenttypes, users
from nti.contentrange import contentrange

from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
from nti.appserver import site_policies

from nti.dataserver.tests import mock_dataserver

from .test_application import ApplicationTestBase

from urllib import quote as UQ

class TestApplicationCoppaAdmin(ApplicationTestBase):

	def test_approve_coppa(self):
		"Basic tests of the moderation admin page"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			coppa_user = self._create_user( username='ossmkitty' )
			interface.alsoProvides( coppa_user, site_policies.IMathcountsCoppaUserWithoutAgreement )
			user_interfaces.IFriendlyNamed( coppa_user ).realname = u'Jason'

		testapp = TestApp( self.app )

		path = '/dataserver2/@@coppa_admin'
		environ = self._make_extra_environ()
		# Have to be in this policy
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'
		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, contains_string( 'ossmkitty' ) )
		assert_that( res.body, contains_string( 'Jason' ) )

		# OK, now let's approve it, then we should be back to an empty page

		form = res.form
		form.set( 'table-coppa-admin-selected-0-selectedItems', True, index=0 )
		res = form.submit( 'subFormTable.buttons.approve', extra_environ=environ )
		assert_that( res.status_int, is_( 302 ) )

		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, does_not( contains_string( 'ossmkitty' ) ) )
		assert_that( res.body, does_not( contains_string( 'Jason' ) ) )

		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'ossmkitty' )
			assert_that( user, verifiably_provides( site_policies.IMathcountsCoppaUserWithAgreement ) )

			assert_that( user_interfaces.IFriendlyNamed( user ), has_property( 'realname', 'Jason' ) )
