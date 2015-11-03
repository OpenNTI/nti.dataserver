#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.appserver.utils.k20.redirect_views import K20_VIEW_NAME
from nti.appserver.utils.k20.redirect_views import K20_LINK_PARAM_NAME

class TestK20Redirect(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True,testapp=True,default_authenticate=True)
	def test_link(self):

		# Redirect link works
		link_val = str( 'http://k20.blah.course/Calculus' )
		params = { K20_LINK_PARAM_NAME : link_val }

		link_url = '/dataserver2/' + K20_VIEW_NAME
		res = self.testapp.get( link_url,
							params=params,
							status=302 )

		# Now get user from token
		user_id = res.location.split( 'token=' )[1]
		user = self.testapp.get( '/dataserver2/Objects/%s' % user_id )
		assert_that( user.json_body.get( 'Username' ), is_( 'sjohnson@nextthought.com'))
