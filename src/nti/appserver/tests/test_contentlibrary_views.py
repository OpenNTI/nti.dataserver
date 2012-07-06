#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from hamcrest import has_property
from . import ConfiguringTestBase
from nti.tests import verifiably_provides
from nti.dataserver.tests.mock_dataserver import WithMockDS, WithMockDSTrans

import anyjson as json
from nti.appserver import interfaces as app_interfaces
from nti.contentlibrary import interfaces as lib_interfaces
from nti.dataserver import users
from nti.dataserver.contenttypes import Note

from zope import interface
from zope.traversing.api import traverse

from nti.appserver.contentlibrary_views import _ContentUnitPreferencesPutView

class TestContainerPrefs(ConfiguringTestBase):

	def setUp( self ):
		config = super(TestContainerPrefs,self).setUp()
		config.testing_securitypolicy( "foo@bar" )

	@WithMockDS
	def test_traverse_container_to_prefs(self):
		user = users.User( "foo@bar" )

		cont_obj = Note()
		cont_obj.containerId = "tag:nextthought.com:foo,bar"

		user.addContainedObject( cont_obj )

		container = user.getContainer( cont_obj.containerId )
		prefs = traverse( container, "++fields++sharingPreference" )
		assert_that( prefs, verifiably_provides( app_interfaces.IContentUnitPreferences ) )

	@WithMockDSTrans
	def test_traverse_content_unit_to_prefs(self):
		user = users.User.create_user( username="foo@bar" )

		cont_obj = Note()
		cont_obj.containerId = "tag:nextthought.com:foo,bar"

		user.addContainedObject( cont_obj )

		@interface.implementer(lib_interfaces.IContentUnit)
		class ContentUnit(object):
			ntiid = cont_obj.containerId

		content_unit = ContentUnit()

		prefs = traverse( content_unit, "++fields++sharingPreference", request=self.request )
		assert_that( prefs, verifiably_provides( app_interfaces.IContentUnitPreferences ) )

	@WithMockDSTrans
	def test_update_shared_with(self):
		user = users.User.create_user( username="foo@bar" )

		cont_obj = Note()
		cont_obj.containerId = "tag:nextthought.com:foo,bar"

		user.addContainedObject( cont_obj )

		@interface.implementer(lib_interfaces.IContentUnit)
		class ContentUnit(object):
			ntiid = cont_obj.containerId
			href = 'prealgebra'

		content_unit = ContentUnit()

		prefs = traverse( content_unit, "++fields++sharingPreference", request=self.request )
		assert_that( prefs, verifiably_provides( app_interfaces.IContentUnitPreferences ) )

		self.request.context = prefs
		self.request.body = json.dumps( {"sharedWith": ['a','b'] } )
		self.request.content_type = 'application/json'

		class Accept(object):
			def best_match( self, *args ): return 'application/json'

		self.request.accept = Accept()
		interface.implementer( lib_interfaces.IContentPackageLibrary )
		class Lib(object):
			titles = ()
			def __getitem__( self, ntiid ):
				return content_unit

		self.request.registry.registerUtility( Lib(), lib_interfaces.IContentPackageLibrary )

		result = _ContentUnitPreferencesPutView(self.request)()

		assert_that( prefs, has_property( 'sharedWith', ['a','b'] ) )
		assert_that( result, verifiably_provides( app_interfaces.IContentUnitInfo ) )
