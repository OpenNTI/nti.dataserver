#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import anyjson as json

from zope import interface
from zope.traversing.api import traverse

from pyramid import traversal

from nti.appserver import interfaces as app_interfaces

import unittest

from nti.contentlibrary import interfaces as lib_interfaces

from nti.dataserver import users
from nti.dataserver.contenttypes import Note
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.ntiids import ntiids

from nti.testing.matchers import verifiably_provides
from pyramid.request import Request
from pyramid.router import Router
from zope import component

from ..library_views import _ContentUnitPreferencesPutView, _ContentUnitPreferencesDecorator
from ..library_views import find_page_info_view_helper
from nti.appserver.httpexceptions import HTTPNotFound

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import has_entry
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import greater_than
from nose.tools import assert_raises

@interface.implementer(lib_interfaces.IContentUnit)
class ContentUnit(object):
	href = 'prealgebra'
	ntiid = None
	__parent__ = None
	lastModified = 0

	def does_sibling_entry_exist( self, sib_name ):
		return None

	def __conform__( self, iface ):
		if iface == lib_interfaces.IContentUnitHrefMapper:
			return NIDMapper( self )

@interface.implementer(lib_interfaces.IContentUnitHrefMapper)
class NIDMapper(object):
	def __init__( self, context ):
		href = context.href
		root_package = traversal.find_interface( context, lib_interfaces.IContentPackage )
		if root_package:
			href = root_package.root + '/' + context.href
		href = href.replace( '//', '/' )
		if not href.startswith( '/' ):
			href = '/' + href

		self.href = href

class ContentUnitInfo(object):
	contentUnit = None
	lastModified = 0


from nti.app.testing.layers import NewRequestLayerTest
from nti.app.testing.layers import NewRequestSharedConfiguringTestLayer
from pyramid.interfaces import IAuthorizationPolicy
from pyramid.interfaces import IAuthenticationPolicy
class _SecurityPolicyNewRequestSharedConfiguringTestLayer(NewRequestSharedConfiguringTestLayer):
	rem_username = 'foo@bar'

	@classmethod
	def setUp(cls):
		config = NewRequestSharedConfiguringTestLayer.config
		cls.__old_author = config.registry.queryUtility(IAuthorizationPolicy)
		cls.__old_authen = config.registry.queryUtility(IAuthenticationPolicy)
		cls.__new_policy = config.testing_securitypolicy(cls.rem_username)


	@classmethod
	def tearDown(cls):
		config = NewRequestSharedConfiguringTestLayer.config
		config.registry.unregisterUtility(cls.__new_policy, IAuthorizationPolicy)
		config.registry.unregisterUtility(cls.__new_policy, IAuthenticationPolicy)
		if cls.__old_author:
			config.registry.registerUtility(cls.__old_author, IAuthorizationPolicy)
		if cls.__old_authen:
			config.registry.registerUtility(cls.__old_authen, IAuthenticationPolicy)

	@classmethod
	def testSetUp(cls):
		pass

	@classmethod
	def testTearDown(cls):
		pass

class TestContainerPrefs(NewRequestLayerTest):
	layer = _SecurityPolicyNewRequestSharedConfiguringTestLayer
	rem_username = layer.rem_username


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


	@WithMockDSTrans
	def test_traverse_container_to_prefs(self):
		user = users.User.create_user( username="foo@bar" )

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

		@interface.implementer( lib_interfaces.IContentPackageLibrary )
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
		# containerId = "tag:nextthought.com:foo,bar"

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

from nti.app.testing.application_webtest import ApplicationLayerTest
from . import ContentLibraryApplicationTestLayer
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.dataserver.tests import mock_dataserver
from urllib import quote

class TestApplication(ApplicationLayerTest):


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_library_main(self):
		href = '/dataserver2/users/sjohnson@nextthought.com/Library/Main'

		service_res = self.testapp.get( '/dataserver2')
		library_ws, = [x for x in service_res.json_body['Items'] if x['Title'] == 'Library']
		assert_that( library_ws, has_entry( 'Items', has_length(1)))
		main_col = library_ws['Items'][0]
		assert_that( main_col, has_entry( 'href', quote(href) ))

		res = self.testapp.get( href )
		assert_that( res.cache_control, has_property( 'max_age', 0 ) )
		assert_that( res.json_body, has_entries( 'href', href,
												 'titles', is_([])))

	@WithSharedApplicationMockDS
	def test_unicode_in_page_href(self):
		with mock_dataserver.mock_db_trans(self.ds):
			unit = ContentUnit()
			unit.ntiid = u'\u2122'
			request = Request.blank('/')
			request.possible_site_names = ()
			request.invoke_subrequest = Router(component.getGlobalSiteManager()).invoke_subrequest
			request.environ['REMOTE_USER'] = 'foo'
			request.environ['repoze.who.identity'] = {'repoze.who.userid': 'foo'}
			with assert_raises(HTTPNotFound):
				find_page_info_view_helper( request, unit )

class TestApplicationBundles(ApplicationLayerTest):

	layer = ContentLibraryApplicationTestLayer

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_bundle_library_main(self):
		href = '/dataserver2/users/sjohnson@nextthought.com/ContentBundles/VisibleContentBundles'

		service_res = self.testapp.get( '/dataserver2')
		library_ws, = [x for x in service_res.json_body['Items'] if x['Title'] == 'ContentBundles']
		assert_that( library_ws, has_entry( 'Items', has_length(1)))
		main_col = library_ws['Items'][0]
		assert_that( main_col, has_entry( 'href', quote(href) ))

		res = self.testapp.get( href )
		assert_that( res.cache_control, has_property( 'max_age', 0 ) )
		assert_that( res.json_body, has_entries( 'href', href,
												 'titles', has_length(1) ) )

		package = res.json_body['titles'][0]

		assert_that( self.require_link_href_with_rel(package, 'DiscussionBoard'),
					 is_('/dataserver2/%2B%2Betc%2B%2Bbundles/bundles/tag%3Anextthought.com%2C2011-10%3ANTI-Bundle-ABundle/DiscussionBoard'))


from nti.app.forums.tests.base_forum_testing import AbstractTestApplicationForumsBaseMixin
from nti.app.forums.tests.base_forum_testing import UserCommunityFixture
from nti.app.forums.tests.base_forum_testing import _plain

from ..forum import ContentForum
from ..forum import ContentBoard
from ..forum import ContentHeadlineTopic

_FORUM_NAME = ContentForum.__default_name__
_BOARD_NAME = ContentBoard.__default_name__


class TestApplicationBundlesForum(AbstractTestApplicationForumsBaseMixin,ApplicationLayerTest):
	__test__ = True

	layer = ContentLibraryApplicationTestLayer

	extra_environ_default_user = AbstractTestApplicationForumsBaseMixin.default_username
	default_community = 'TheCommunity'
	default_entityname = default_community
	#default_community = 'zope.security.management.system_user'
	#default_entityname = default_community

	forum_url_relative_to_user = _BOARD_NAME + '/' + _FORUM_NAME

	board_ntiid = None
	board_content_type = None

	forum_ntiid = None
	forum_topic_ntiid_base = None


	forum_content_type = 'application/vnd.nextthought.forums.contentforum+json'
	forum_headline_class_type = 'Post'
	forum_topic_content_type = None
	board_link_rel = forum_link_rel = _BOARD_NAME
	forum_title = _FORUM_NAME
	forum_type = ContentForum

	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.contentforumcomment+json'

	check_sharedWith_community = False

	def setUp( self ):
		super(TestApplicationBundlesForum,self).setUp()
		self.forum_pretty_url = '/dataserver2/%2B%2Betc%2B%2Bbundles/bundles/tag%3Anextthought.com%2C2011-10%3ANTI-Bundle-ABundle/DiscussionBoard/Forum'
		self.forum_pretty_contents_url = self.forum_pretty_url + '/contents'
		self.board_pretty_url = self.forum_pretty_url[:-(len(_FORUM_NAME) + 1)]

		self.board_content_type = ContentBoard.mimeType + '+json'
		self.forum_topic_content_type = ContentHeadlineTopic.mimeType + '+json'

		self.forum_ntiid_url = None

	def test_user_can_POST_new_forum_entry_resulting_in_blog_being_sublocation( self ):
		pass # not applicable
