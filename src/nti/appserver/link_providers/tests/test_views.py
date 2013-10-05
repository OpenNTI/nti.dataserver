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
from hamcrest import has_item

import nti.testing.base

from zope import interface
from zope.component.hooks import site
from nti.dataserver.site import _TrivialSite
from nti.appserver.policies.sites import BASECOPPA as MATHCOUNTS

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.appserver.httpexceptions import HTTPNotFound, HTTPNoContent, HTTPSeeOther
from pyramid.request import Request

from .test_zcml import ZCML_STRING

from ..views import named_link_get_view
from ..views import named_link_delete_view

class TestViews(nti.testing.base.ConfiguringTestBase):

	def setUp( self ):
		super(TestViews,self).setUp()
		self.configure_string( ZCML_STRING )
		self.user = users.User( 'foo@bar' )
		self.request = Request.blank( '/' )
		self.request.subpath = ()
		self.request.context = self.user

	def _test_common( self, view ):
		request = self.request
		# no subpath
		assert_that( view( request ), is_( HTTPNotFound ) )

		# wrong subpath
		request.subpath = ('unregistered',)
		assert_that( view( request ), is_( HTTPNotFound ) )

		# right subpath, wrong user type
		request.subpath = ('foo.bar',)
		assert_that( view( request ), is_( HTTPNotFound ) )

	def test_get_view(self):
		with site( _TrivialSite( MATHCOUNTS ) ):
			self._test_common( named_link_get_view )

			# finally the stars align
			interface.alsoProvides( self.user, nti_interfaces.ICoppaUser )
			result = named_link_get_view( self.request )
			assert_that( result, is_( HTTPSeeOther ) )
			assert_that( result.location, is_( '/relative/path' ) )
			# made absolute on output
			headerlist = []
			def start_request( status, headers ):
				headerlist.extend( headers )
			result( self.request.environ, start_request )
			assert_that( headerlist, has_item( ('Location', 'http://localhost/relative/path') ) )

	def test_get_view_wrong_site(self):
		self._test_common( named_link_get_view )

		interface.alsoProvides( self.user, nti_interfaces.ICoppaUser )
		assert_that( named_link_get_view( self.request ), is_( HTTPNotFound ) )


	def test_delete_view(self):
		with site( _TrivialSite( MATHCOUNTS ) ):
			self._test_common( named_link_delete_view )

			# finally the stars align
			interface.alsoProvides( self.user, nti_interfaces.ICoppaUser )
			assert_that( named_link_delete_view( self.request ), is_( HTTPNoContent ) )

			# Doing it again is not found
			assert_that( named_link_delete_view( self.request ), is_( HTTPNotFound ) )

			# As is a get
			assert_that( named_link_get_view( self.request ), is_( HTTPNotFound ) )
