#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

#pylint: disable=R0904

from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import has_entry
from hamcrest import has_key
from hamcrest import greater_than

from nti.appserver.tests import NewRequestSharedConfiguringTestBase
from nti.tests import verifiably_provides
from nti.dataserver.tests.mock_dataserver import WithMockDS, WithMockDSTrans

import anyjson as json
from nti.appserver import interfaces as app_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.ntiids import ntiids

from zope import interface
from zope.traversing.api import traverse

from nti.appserver.contentlibrary_views import _ContentUnitPreferencesPutView, _ContentUnitPreferencesDecorator

@interface.implementer(lib_interfaces.IContentUnit)
class ContentUnit(object):
	href = 'prealgebra'
	ntiid = None
	__parent__ = None
	lastModified = 0

class ContentUnitInfo(object):
	contentUnit = None
	lastModified = 0


class TestContainerPrefs(NewRequestSharedConfiguringTestBase):

	rem_username = 'foo@bar'

	def setUp( self ):
		config = super(TestContainerPrefs,self).setUp()
		config.testing_securitypolicy( self.rem_username )

	def _do_check_root_inherited(self, ntiid=None, sharedWith=None, state='inherited', provenance=ntiids.ROOT):

		unit = ContentUnit()
		unit.ntiid = ntiid
		# Notice that the root is missing from the lineage

		info = ContentUnitInfo()
		info.contentUnit = unit
		decorator = _ContentUnitPreferencesDecorator( info )
		result_map = {}

		decorator.decorateExternalMapping( info, result_map )

		assert_that( result_map, has_entry( 'sharingPreference',
											has_entry( 'State', state ) ) )

		assert_that( result_map, has_entry( 'sharingPreference',
											has_entry( 'Provenance', provenance ) ) )
		assert_that( result_map, has_entry( 'sharingPreference',
											has_entry( 'sharedWith', sharedWith ) ) )
		if sharedWith:
			assert_that( result_map, has_key( 'Last Modified' ) )
			assert_that( info, has_property( 'lastModified', greater_than( 0 ) ) )

	@WithMockDSTrans
	def test_decorate_inherit(self):
		user = users.User.create_user( username=self.rem_username )

		cid = "tag:nextthought.com:foo,bar"
		root_cid = ''

		# Create the containers
		for c in (cid,root_cid):
			user.containers.getOrCreateContainer( c )

		# Add sharing prefs to the root
		prefs = app_interfaces.IContentUnitPreferences( user.getContainer( root_cid ) )
		prefs.sharedWith = ['a@b']

		self._do_check_root_inherited( ntiid=cid, sharedWith=['a@b'] )

		# Now, if we set something at the leaf node, then it trumps
		cid_prefs = app_interfaces.IContentUnitPreferences( user.getContainer( cid ) )
		cid_prefs.sharedWith = ['leaf']

		self._do_check_root_inherited( ntiid=cid, sharedWith=['leaf'], state='set', provenance=cid )

		# Even setting something blank at the leaf trumps
		cid_prefs.sharedWith = []

		self._do_check_root_inherited( ntiid=cid, sharedWith=[], state='set', provenance=cid )

		# But if we delete it from the leaf, we're back to the root
		cid_prefs.sharedWith = None
		self._do_check_root_inherited( ntiid=cid, sharedWith=['a@b'] )


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
		user = users.User.create_user( username=self.rem_username )

		cont_obj = Note()
		cont_obj.containerId = "tag:nextthought.com:foo,bar"

		user.addContainedObject( cont_obj )

		content_unit = ContentUnit()
		content_unit.ntiid = cont_obj.containerId

		prefs = traverse( content_unit, "++fields++sharingPreference", request=self.request )
		assert_that( prefs, verifiably_provides( app_interfaces.IContentUnitPreferences ) )

	def _do_update_prefs( self, content_unit, sharedWith=None ):
		self.request.method = 'PUT'
		prefs = traverse( content_unit, "++fields++sharingPreference", request=self.request )
		assert_that( prefs, verifiably_provides( app_interfaces.IContentUnitPreferences ) )

		self.request.context = prefs
		self.request.body = json.dumps( {"sharedWith": sharedWith } )
		self.request.content_type = 'application/json'


		class Accept(object):
			def best_match( self, *args ): return 'application/json'

		self.request.accept = Accept()

		interface.implementer( lib_interfaces.IContentPackageLibrary )
		class Lib(object):
			titles = ()
			def pathToNTIID( self, ntiid ):
				return [content_unit]

		self.request.registry.registerUtility( Lib(), lib_interfaces.IContentPackageLibrary )

		result = _ContentUnitPreferencesPutView(self.request)()

		assert_that( prefs, has_property( 'sharedWith', sharedWith ) )
		assert_that( result, verifiably_provides( app_interfaces.IContentUnitInfo ) )

	@WithMockDSTrans
	def test_update_shared_with_in_preexisting_container(self):

		user = users.User.create_user( username=self.rem_username )
		# Make the container exist
		cont_obj = Note()
		cont_obj.containerId = "tag:nextthought.com:foo,bar"
		user.addContainedObject( cont_obj )


		content_unit = ContentUnit()
		content_unit.ntiid = cont_obj.containerId

		self._do_update_prefs( content_unit, sharedWith=['a','b']  )

	@WithMockDSTrans
	def test_update_shared_with_in_non_existing_container(self):

		_ = users.User.create_user( username=self.rem_username )
		# Note the container does not exist
		containerId = "tag:nextthought.com:foo,bar"

		content_unit = ContentUnit()
		content_unit.ntiid = containerId

		# The magic actually happens during traversal
		# That's why the method must be 'PUT' before traversal
		self._do_update_prefs( content_unit, sharedWith=['a','b'] )


	@WithMockDSTrans
	def test_update_shared_with_in_root_inherits(self):

		_ = users.User.create_user( username=self.rem_username )
		# Note the container does not exist
		containerId = "tag:nextthought.com:foo,bar"

		content_unit = ContentUnit()
		content_unit.ntiid = ntiids.ROOT

		self._do_update_prefs( content_unit, sharedWith=['a','b'] )

		self._do_check_root_inherited( ntiid=containerId, sharedWith=['a','b'] )


	@WithMockDSTrans
	def test_prefs_from_content_unit(self):
		_ = users.User.create_user( username=self.rem_username )
		# Note the container does not exist
		containerId = "tag:nextthought.com:foo,bar"

		content_unit = ContentUnit()
		content_unit.ntiid = ntiids.ROOT

		interface.alsoProvides( content_unit, app_interfaces.IContentUnitPreferences )
		content_unit.sharedWith = ['2@3']

		info = ContentUnitInfo()
		info.contentUnit = content_unit
		decorator = _ContentUnitPreferencesDecorator( info )
		result_map = {}

		decorator.decorateExternalMapping( info, result_map )

		assert_that( result_map, has_entry( 'sharingPreference',
											has_entry( 'State', 'set' ) ) )

		assert_that( result_map, has_entry( 'sharingPreference',
											has_entry( 'sharedWith', ['2@3'] ) ) )
