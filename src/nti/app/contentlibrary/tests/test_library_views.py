#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


from zope import interface

from pyramid import traversal

from nti.contentlibrary import interfaces as lib_interfaces

from pyramid.request import Request
from pyramid.router import Router
from zope import component


from ..library_views import find_page_info_view_helper
from nti.appserver.httpexceptions import HTTPNotFound

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import calling
from hamcrest import raises


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
			assert_that( calling(find_page_info_view_helper).with_args(request, unit),
						 raises(HTTPNotFound))


class TestApplicationContent(ApplicationLayerTest):
	layer = ContentLibraryApplicationTestLayer

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_sub_page_info(self):

		href = '/dataserver2/NTIIDs/tag:nextthought.com,2011-10:USSC-HTML-Cohen.22'

		res = self.testapp.get(href,
							   headers={b"Accept": b'application/json' })

		href = self.require_link_href_with_rel(res.json_body, 'content')
		assert_that( href, is_('/TestFilesystem/tag_nextthought_com_2011-10_USSC-HTML-Cohen_18.html#22') )


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
