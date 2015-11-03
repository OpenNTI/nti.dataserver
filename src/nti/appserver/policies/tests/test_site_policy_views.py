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
from hamcrest import is_
from hamcrest import has_property
import fudge


from nti.app.testing.request_response import DummyRequest
from nti.app.testing.request_response import ByteHeadersResponse

from ..site_policy_views import webapp_strings_view

class TestViews(unittest.TestCase):

	def test_webapp_strings_view_not_found(self):

		request = DummyRequest.blank(b'/foo/bar/site.js')
		request.possible_site_names = ('dne.example.com',)
		request.response = ByteHeadersResponse()
		webapp_strings_view(request)

		for k, v in request.environ.items():
			assert_that( k, is_( bytes ) )
			if isinstance(v, basestring):
				assert_that( v, is_( bytes ) )

	@fudge.patch('nti.appserver.policies.site_policies.queryUtilityInSite')
	def test_webapp_strings_view_legacy_found(self, mock_query):
		mock_query.is_callable().returns( (object, u'site.example.com') )


		request = DummyRequest.blank(b'/foo/bar/site.js')
		request.possible_site_names = (u'site.example.com',)
		request.response = ByteHeadersResponse()

		def _resource_path( context, *args ):
			return b'/'.join( args )
		request.resource_path = _resource_path
		request.context = None
		rsp = webapp_strings_view(request)

		for k, v in request.environ.items():
			assert_that( k, is_( bytes ) )
			if isinstance(v, basestring):
				assert_that( v, is_( bytes ) )

		assert_that( rsp, has_property( 'location', is_(bytes) ) )
		assert_that( rsp, has_property( 'location', is_('foo/bar/site.example.com/strings.js') ) )
		for k, v in rsp.headerlist:
			assert_that( k, is_( bytes ) )
			assert_that( v, is_( bytes ) )
