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
from hamcrest import is_not as does_not
is_not = does_not
from hamcrest import contains
from hamcrest import has_entry


from nti.tests import time_monotonically_increases

from nti.dataserver.contenttypes.forums.forum import  CommunityForum
from nti.dataserver.contenttypes.forums.topic import  CommunityHeadlineTopic


from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS


from pyquery import PyQuery


# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext


from .base_forum_testing import AbstractTestApplicationForumsBase
from .base_forum_testing import UserCommunityFixture


class TestApplicationCommunityForums(AbstractTestApplicationForumsBase):
	__test__ = True

	features = SharedApplicationTestBase.features + ('forums',)
	extra_environ_default_user = AbstractTestApplicationForumsBase.default_username
	default_community = 'TheCommunity'
	default_entityname = default_community
	forum_url_relative_to_user = 'Forum'
	forum_ntiid = 'tag:nextthought.com,2011-10:TheCommunity-Forum:GeneralCommunity-Forum'
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:TheCommunity-Topic:GeneralCommunity-'

	forum_content_type = 'application/vnd.nextthought.forums.communityforum+json'
	forum_headline_class_type = 'Post'
	forum_topic_content_type = CommunityHeadlineTopic.mimeType + '+json'
	forum_link_rel = 'Forum'
	forum_title = forum_link_rel
	forum_type = CommunityForum

	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.generalforumcomment+json'

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_default_forum_in_links( self ):
		# Default forum is present in the community links
		user = self.resolve_user(username=self.default_community)
		href = self.require_link_href_with_rel( user, self.forum_link_rel )
		assert_that( href, is_( self.forum_pretty_url ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_forum_entry_class( self ):
		"""POSTing an IPost to the forum URL automatically creates a new topic"""

		# With a Class value:
		data = { 'Class': self.forum_headline_class_type,
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		self._do_test_user_can_POST_new_forum_entry( data )


	def _do_test_user_can_POST_new_forum_entry( self, data, content_type=None, status_only=None, expected_data=None ):
		res = self._do_simple_tests_for_POST_of_topic_entry( data, content_type=content_type, status_only=status_only, expected_data=expected_data )
		if status_only:
			return res
		testapp = self.testapp

		# Returns the representation of the new topic created
		data = expected_data or data
		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		entry_id = res.json_body['ID']
		headline_json = res.json_body['headline']

		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']

		# The new topic is accessible at its OID URL, its pretty URL, and by NTIID (not yet)
		for url in entry_url, self.forum_topic_href( entry_id ):  #, UQ( '/dataserver2/NTIIDs/' + entry_ntiid ):
			testapp.get( url )


		# and it has no contents
		testapp.get( contents_href, status=200 )

		# It shows up in the blog contents
		res = testapp.get( self.forum_pretty_contents_url )
		blog_items = res.json_body['Items']
		assert_that( blog_items, contains( has_entry( 'title', data['title'] ) ) )
		# With its links all intact
		blog_item = blog_items[0]
		assert_that( blog_item, has_entry( 'href', self.forum_topic_href( blog_item['ID'] ) ))
		self.require_link_href_with_rel( blog_item, 'contents' )
		#self.require_link_href_with_rel( blog_item, 'like' ) # entries can be liked
		#self.require_link_href_with_rel( blog_item, 'flag' ) # entries can be flagged
		#self.require_link_href_with_rel( blog_item, 'edit' ) # entries can be 'edited' (actually they cannot)


		# It also shows up in the blog's data feed (partially rendered in HTML)
		res = testapp.get( self.forum_pretty_url + '/feed.atom' )
		assert_that( res.content_type, is_( 'application/atom+xml'))
		res._use_unicode = False
		pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.
		assert_that( pq( b'entry title' ).text(), is_( data['title'] ) )
		assert_that( pq( b'entry summary' ).text(), is_( '<div><br />' + data['body'][0] ) )


		# And in the user activity view
		#res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Activity' )
		#assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		#assert_that( res.json_body['Items'], has_length( 1 ) ) # make sure no dups

		# And in the user root recursive data stream
		#res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData' )
		#assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )

		# and, if favorited, filtered to the favorites
		#testapp.post( fav_href )
		#res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData',
		#				   params={'filter': 'Favorite'})
		#assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		#self.require_link_href_with_rel( res.json_body['Items'][0], 'unfavorite' )


	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_creator_cannot_DELETE_community_user_comment_in_published_topic(self):
		fixture = UserCommunityFixture( self )
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location

		# non-creator comment
		comment_data = self._create_comment_data_for_POST()
		comment_res = testapp2.post_json( topic_url, comment_data, status=201 )
		edit_href = self.require_link_href_with_rel( comment_res.json_body, 'edit' )

		# cannot be deleted by created
		res = testapp.delete( edit_href, status=403 ) # forbidden by ACL
