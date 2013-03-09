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
from hamcrest import has_key
from hamcrest import has_entry

import nti.tests

from zope import interface
from zope.component.hooks import site
from nti.dataserver.site import _TrivialSite
from nti.appserver.sites import MATHCOUNTS

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.appserver.httpexceptions import HTTPNotFound, HTTPNoContent, HTTPForbidden, HTTPSeeOther
from pyramid.request import Request

from .test_zcml import ZCML_STRING

from ..views import named_link_get_view
from ..views import named_link_delete_view

class TestViews(nti.tests.ConfiguringTestBase):

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
			assert_that( named_link_get_view( self.request ), is_( HTTPSeeOther ) )

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
