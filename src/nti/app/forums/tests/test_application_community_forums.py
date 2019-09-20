#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import not_none
from hamcrest import contains
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import greater_than
does_not = is_not

import fudge

from Queue import Queue

from six.moves.urllib_parse import quote
UQ = quote

from pyquery import PyQuery

from webob.request import environ_from_url

from zope.component import eventtesting

from zope.component.hooks import getSite

from zope.lifecycleevent import IObjectRemovedEvent

from zope.intid.interfaces import IIntIdRemovedEvent

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.asynchronous.scheduled.redis_queue import ScheduledQueue

from nti.dataserver.contenttypes.forums.forum import DEFAULT_FORUM_KEY
from nti.dataserver.contenttypes.forums.forum import DEFAULT_FORUM_NAME

from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums.board import CommunityBoard
from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic

_FORUM_NAME = DEFAULT_FORUM_KEY
_BOARD_NAME = CommunityBoard.__default_name__

from nti.app.testing.webtest import TestApp as _TestApp
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

from nti.app.forums.tests.base_forum_testing import UserCommunityFixture
from nti.app.forums.tests.base_forum_testing import AbstractTestApplicationForumsBaseMixin

from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.contenttypes.forums.interfaces import ICommunityAdminRestrictedForum
from nti.dataserver.contenttypes.forums.interfaces import ISendEmailOnForumTypeCreation

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users import Community

from nti.dataserver.users.common import set_entity_creation_site

from nti.mailer.interfaces import IEmailAddressable

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.testing.matchers import verifiably_provides

from nti.testing.time import time_monotonically_increases


class TestApplicationCommunityForums(AbstractTestApplicationForumsBaseMixin,
									 ApplicationLayerTest):
	__test__ = True

	extra_environ_default_user = AbstractTestApplicationForumsBaseMixin.default_username

	default_community = 'TheCommunity'
	default_entityname = default_community
	forum_url_relative_to_user = _BOARD_NAME + '/' + _FORUM_NAME
	forum_ntiid = None
	forum_topic_ntiid_base = None
	forum_ntiid_url = None
	board_ntiid_checker = not_none()
	board_content_type = None

	forum_content_type = 'application/vnd.nextthought.forums.communityforum+json'
	forum_headline_class_type = 'Post'
	forum_topic_content_type = None
	board_link_rel = forum_link_rel = _BOARD_NAME
	forum_title = DEFAULT_FORUM_NAME
	forum_type = CommunityForum

	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.generalforumcomment+json'

	def setUp( self ):
		super(TestApplicationCommunityForums,self).setUp()
		self.board_pretty_url = self.forum_pretty_url[:-(len(quote(_FORUM_NAME)) + 1)]

		self.board_content_type = CommunityBoard.mimeType + '+json'
		self.forum_topic_content_type = CommunityHeadlineTopic.mimeType + '+json'

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_default_board_in_links( self ):
		# Default board is present in the community links
		user = self.resolve_user(username=self.default_community)
		href = self.require_link_href_with_rel( user, self.board_link_rel )
		assert_that( href, is_( self.board_pretty_url ) )

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	@time_monotonically_increases
	def test_super_user_can_edit_forum_description(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		board_res = adminapp.get( self.board_pretty_url )
		board_contents = self.require_link_href_with_rel(board_res.json_body, 'contents')
		board_contents_res = adminapp.get(board_contents)

		adminapp.put_json( forum_res.location, {'description': 'The updated description'} )

		forum_res = self.testapp.get( forum_res.location )
		assert_that( forum_res.json_body, has_entry( 'description', "The updated description" ) )

		# And when we get the board again, it shows up as changed
		adminapp.get( board_contents,
					  headers={b'If-None-Match': board_contents_res.etag,
							   b'If-Modified-Since': board_contents_res.headers['Last-Modified']},
					  status=200)

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	def test_super_user_can_edit_forum_description_using_field(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		adminapp.put_json( forum_res.location + '++fields++description', 'The updated description' )

		forum_res = self.testapp.get( forum_res.location )
		assert_that( forum_res.json_body, has_entry( 'description', "The updated description" ) )

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	def test_super_user_can_delete_forum(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		# Normal user cannot
		self.testapp.delete( forum_res.location, status=403 )

		# admin can
		eventtesting.clearEvents()
		adminapp.delete( forum_res.location, status=204 )

		rem_events = eventtesting.getEvents(IObjectRemovedEvent)
		assert_that( rem_events, has_length( 1 ) )
		self.testapp.get( forum_res.location, status=404 )

	@time_monotonically_increases
	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	def test_board_sorted_contents(self):
		"""
		Test users can define our board sorting order
		"""
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_data1 = dict(forum_data)
		forum_data2 = dict(forum_data)
		forum_data3 = dict(forum_data)
		forum_data1['title'] = forum_title1 = 'forum data 1'
		forum_data2['title'] = forum_title2 = 'forum data 2'
		forum_data3['title'] = forum_title3 = 'forum data 3'
		forum_res1 = adminapp.post_json(self.board_pretty_url, forum_data1)
		forum_res2 = adminapp.post_json(self.board_pretty_url, forum_data2)
		forum_res3 = adminapp.post_json(self.board_pretty_url, forum_data3)
		forum_ntiid1 = forum_res1.json_body.get('NTIID')
		forum_ntiid2 = forum_res2.json_body.get('NTIID')
		forum_ntiid3 = forum_res3.json_body.get('NTIID')
		assert_that(forum_ntiid1, not_none())
		assert_that(forum_ntiid2, not_none())
		assert_that(forum_ntiid3, not_none())
		res = adminapp.get(self.board_pretty_url)
		contents_href = self.require_link_href_with_rel(res.json_body, 'contents')

		default_forum = adminapp.get('%s/%s' % (self.board_pretty_url, DEFAULT_FORUM_KEY))
		default_forum_ntiid = default_forum.json_body.get('NTIID')
		def get_forum_titles(reverse=False):
			href = contents_href
			if reverse:
				href = '%s?sortOrder=descending' % href
			contents = adminapp.get(href).json_body
			return [x.get('title') for x in contents['Items']]
		# By default, sorted by last mod
		assert_that(get_forum_titles(), contains(DEFAULT_FORUM_NAME,
												 forum_title1,
												 forum_title2,
												 forum_title3))

		#adminapp.put_json('%s/++fields++ordered_keys' % self.board_pretty_url, [forum_ntiid3, forum_ntiid2])
		adminapp.put_json(self.board_pretty_url,
						  {'ordered_keys': [forum_ntiid3, forum_ntiid2]})
		assert_that(get_forum_titles(), contains(forum_title3,
												 forum_title2,
												 DEFAULT_FORUM_NAME,
												 forum_title1))
		# When state changes, validate an extraneous value does not break things
		adminapp.put_json(self.board_pretty_url,
						  {'ordered_keys': [default_forum_ntiid, 'dne_ntiid', forum_ntiid3, forum_ntiid2]})
		assert_that(get_forum_titles(), contains(DEFAULT_FORUM_NAME,
												 forum_title3,
												 forum_title2,
												 forum_title1))

		# Reversed
		assert_that(get_forum_titles(reverse=True), contains(forum_title1,
															 forum_title2,
															 forum_title3,
															 DEFAULT_FORUM_NAME))

		# Now undo
		adminapp.put_json(self.board_pretty_url, {'ordered_keys': []})
		assert_that(get_forum_titles(), contains(DEFAULT_FORUM_NAME,
												 forum_title1,
												 forum_title2,
												 forum_title3))
		self.testapp.put_json(self.board_pretty_url,
							  {'ordered_keys': [forum_ntiid3, forum_ntiid2]},
							  status=403)

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	def test_super_user_can_delete_forum_with_topic_and_comments(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		# now community user publishes
		publish_res, _ = self._POST_and_publish_topic_entry( forum_url=forum_res.location )

		# and for grins, community user comments on own topic
		comment_res = self.testapp.post_json( publish_res.json_body['href'], self._create_comment_data_for_POST() )

		# now the admin can delete the forum, destroying the forum,
		# the topic, the headline post, and the comment
		eventtesting.clearEvents()
		adminapp.delete( forum_res.location, status=204 )
		# There's only one ObjectRemovedEvent, but it is dispatched
		# to all the sublocations
		rem_events = eventtesting.getEvents(IObjectRemovedEvent)
		assert_that( rem_events, has_length( 1 ) )

		# So all four of the objects got their intid removed
		int_rem_events = eventtesting.getEvents(IIntIdRemovedEvent)
		assert_that( int_rem_events, has_length( 4 ) )
		# So all the locations 404
		for res in forum_res, publish_res, comment_res:
			self.testapp.get( res.location, status=404 )

	def _do_test_user_can_POST_new_forum_entry( self, data, content_type=None, status_only=None, expected_data=None ):
		# Override the method in super()
		activity_res = self.fetch_user_activity()
		post_res = self._do_simple_tests_for_POST_of_topic_entry( data, content_type=content_type, status_only=status_only, expected_data=expected_data )
		if status_only:
			return post_res
		testapp = self.testapp
		res = post_res
		# Returns the representation of the new topic created
		data = expected_data or data
		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		entry_id = res.json_body['ID']
		assert_that( res.json_body, has_key( 'headline' ) )
		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']

		# The new topic is accessible at its OID URL, its pretty URL, and by NTIID
		for url in entry_url, self.forum_topic_href( entry_id ), UQ( '/dataserver2/NTIIDs/' + entry_ntiid ):
			testapp.get( url )

		# and it has no contents
		testapp.get( contents_href, status=200 )

		# It shows up in the forum contents
		res = testapp.get( self.forum_pretty_contents_url )
		blog_items = res.json_body['Items']
		assert_that( blog_items, contains( has_entry( 'title', data['title'] ) ) )
		# With its links all intact
		blog_item = blog_items[0]
		assert_that( blog_item, has_entry( 'href', self.forum_topic_href( blog_item['ID'] ) ))
		self.require_link_href_with_rel( blog_item, 'contents' )

		# It also shows up in the blog's data feed (partially rendered in HTML)
		res = testapp.get( self.forum_pretty_url + '/feed.atom' )
		assert_that( res.content_type, is_( 'application/atom+xml'))
		res._use_unicode = False
		pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.
		assert_that( pq( b'entry title' ).text(), is_( data['title'] ) )
		assert_that( pq( b'entry summary' ).text(), is_( '<div><br />' + data['body'][0] + '</div>' ) )

		# It shows up in the activity stream for the creator, and
		# the modification date and etag of the data changed
		new_activity_res = self.fetch_user_activity()
		assert_that( new_activity_res.json_body['Items'], has_item(has_entry('NTIID', entry_ntiid)))
		assert_that(new_activity_res.last_modified, is_not(none()))
		assert_that( new_activity_res.last_modified, is_( greater_than( activity_res.last_modified )))
		assert_that( new_activity_res.etag, is_not(activity_res.etag))
		return post_res

	@WithSharedApplicationMockDS
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

		# cannot be deleted by creator
		testapp.delete( edit_href, status=403 ) # forbidden by ACL

	@WithSharedApplicationMockDS
	def test_community_topics_and_comments_in_RUGD_and_RSTREAM(self):
		fixture = UserCommunityFixture( self )
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location

		# The creator of the community topic doesn't see it in his RUGD
		# without applying some filters
		self.fetch_user_root_rugd( testapp, fixture.user_username, status=404 )

		res = self.fetch_user_root_rugd(testapp, fixture.user_username,
										params={'filter': 'MeOnly',
												'accept': 'application/vnd.nextthought.forums.communityheadlinetopic'})
		assert_that(res.json_body, has_entry('FilteredTotalItemCount', 1))
		assert_that(res.json_body, has_entry('TotalItemCount', 2)) # Both topic and comment
		assert_that(res.json_body['Items'], has_item(has_entry('title', publish_res.json_body['title'])) )

		# Now, the non-creator has the topic in his stream as created
		res = self.fetch_user_root_rstream( testapp2, fixture.user2_username )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
		assert_that( res.json_body['Items'][0], has_entry( 'ChangeType', 'Shared' ) )
		created_event_time = res.json_body['Items'][0]['Last Modified']

		# non-creator adds comment
		comment_data = self._create_comment_data_for_POST()
		testapp2.post_json( topic_url, comment_data, status=201 )

		# the creator gets the comment, but not the topic in his stream (because he created it)
		res = self.fetch_user_root_rstream( testapp, fixture.user_username )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
		assert_that( res.json_body['Items'][0], has_entry( 'ChangeType', 'Created' ) )

		# For the commenter, the comment did not change the event in the stream for the topic, it stays
		# exactly the same
		res = self.fetch_user_root_rstream( testapp2, fixture.user2_username )#, status=404 )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
		assert_that( res.json_body['Items'][0], has_entries( 'ChangeType', 'Shared',
															 'Last Modified', created_event_time ) )


		# The creator of the topic never sees it in his RUGD, not
		# even after a comment is added
		self.fetch_user_root_rugd( testapp, fixture.user_username, status=404 )

		# The commentor also has neither the topic he didn't create,
		# nor the comment he did create, in his RUGD, without applying filters
		self.fetch_user_root_rugd( testapp2, fixture.user2_username, status=404 )

		res = self.fetch_user_root_rugd( testapp2, fixture.user2_username, params={'filter': 'MeOnly'})
		assert_that( res.json_body, has_entry('TotalItemCount', 1) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_creator_cannot_change_sharing_on_community_topic( self ):
		#""" Sharing is fixed and cannot be changed for a blog entry, its story, or a comment"""

		testapp = self.testapp
		res = self._POST_topic_entry()

		topic_url = res.location
		self.require_link_href_with_rel(res.json_body['headline'], 'edit')

		eventtesting.clearEvents()

		# Field updates
		# Cannot change the entry
		testapp.put_json( topic_url + '/++fields++sharedWith',
						  ['Everyone'],
						  # Because of the way traversal is right now, this results in a 404,
						  # when really we want a 403
						  status=404)
		# Nor when putting the whole thing
		# The entry itself simply cannot be modified (predicate mismatch right now)
		testapp.put_json( topic_url,
						  {'sharedWith': ['Everyone']},
						  status=403 )

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_last_modified_changes_when_new_topic_added_published(self):
		fixture = UserCommunityFixture( self )
		self.testapp = fixture.testapp

		self._POST_and_publish_topic_entry()
		forum_res = self.testapp.get( self.forum_pretty_url )
		forum_contents_href = self.require_link_href_with_rel( forum_res.json_body, 'contents' )

		forum_contents_res = self.testapp.get( forum_contents_href )
		assert_that( forum_contents_res.json_body, has_entry( 'TotalItemCount', 1 ) )

		self._POST_and_publish_topic_entry() # create a second one

		forum_contents_res2 = self.testapp.get( forum_contents_href,
												headers={b'If-None-Match': forum_contents_res.etag,
														 b'If-Modified-Since': forum_contents_res.headers['Last-Modified']},
												status=200)

		assert_that( forum_contents_res2.json_body, has_entry( 'TotalItemCount', 2 ) )

		forum_contents_res3 = self.testapp.get( forum_contents_href,
												params={b'searchTerm': 'notfound'},
												status=200)

		assert_that(forum_contents_res3.json_body, has_entry('FilteredTotalItemCount', 0))

		forum_contents_res3 = self.testapp.get(forum_contents_href,
											   params={b'searchTerm': 'blog'},
											   status=200)

		assert_that(forum_contents_res3.json_body, has_entry(u'TotalItemCount', 2))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_last_modified_changes_when_new_topic_title_changed(self):
		fixture = UserCommunityFixture( self )
		self.testapp = fixture.testapp

		topic_res, _ = self._POST_and_publish_topic_entry()
		forum_res = self.testapp.get( self.forum_pretty_url )
		forum_contents_href = self.require_link_href_with_rel( forum_res.json_body, 'contents' )

		forum_contents_res = self.testapp.get( forum_contents_href )
		assert_that( forum_contents_res.json_body, has_entry( 'TotalItemCount', 1 ) )

		self.testapp.put_json( topic_res.json_body['headline']['href'], {'title': "A new and different title"} )

		self.testapp.get(forum_contents_href,
						 headers={b'If-None-Match': forum_contents_res.etag,
								  b'If-Modified-Since': forum_contents_res.headers['Last-Modified']},
						 status=200)

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_board_last_modified_changes_when_new_topic_added_to_forum(self):
		fixture = UserCommunityFixture( self )
		self.testapp = fixture.testapp

		board_pretty_url = '/dataserver2/users/' + self.default_entityname + '/' + _BOARD_NAME

		self._POST_and_publish_topic_entry()
		board_res = self.testapp.get( board_pretty_url )
		board_contents_href = self.require_link_href_with_rel( board_res.json_body, 'contents' )

		board_contents_res = self.testapp.get( board_contents_href )
		assert_that( board_contents_res.json_body, has_entry( 'TotalItemCount', 1 ) )

		self._POST_and_publish_topic_entry() # create a second one

		board_contents_res2 = self.testapp.get( board_contents_href,
												headers={b'If-None-Match': board_contents_res.etag,
														 b'If-Modified-Since': board_contents_res.headers['Last-Modified']},
												status=200)

		assert_that( board_contents_res2.json_body, has_entry( 'TotalItemCount', 1 ) )

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	@fudge.patch('nti.asynchronous.scheduled.utils.get_scheduled_queue')
	@fudge.patch('nti.dataserver.contenttypes.forums.job.send_creation_notification_email')
	def test_notify_on_topic_creation(self, fake_queue, fake_email):
		queue = Queue()
		fake_queue.is_callable().returns(queue)
		with mock_dataserver.mock_db_trans(self.ds):
			default_community = Community.get_community(self.default_community)
			num_members = default_community.number_of_members()
			for member in default_community.iter_members():
				addressable = IEmailAddressable(member)
				addressable.email = u'somevalidemail@test.com'
		fake_email.is_callable().expects_call().times_called(num_members)  # Check this is called for each member

		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()

		# Create with it
		forum_data['notify_on_topic_creation'] = True
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )
		forum_location = forum_res.location
		forum_ntiid = forum_res.json_body['NTIID']
		with mock_dataserver.mock_db_trans(self.ds):
			forum = find_object_with_ntiid(forum_ntiid)
			assert_that(forum, verifiably_provides(ISendEmailOnForumTypeCreation))

		# Disable via PUT
		forum_data['notify_on_topic_creation'] = False
		forum_res = adminapp.put_json( forum_location, forum_data )
		forum_ntiid = forum_res.json_body['NTIID']
		with mock_dataserver.mock_db_trans(self.ds):
			forum = find_object_with_ntiid(forum_ntiid)
			assert_that(forum, does_not(verifiably_provides(ISendEmailOnForumTypeCreation)))

		# Enable via PUT
		forum_data['notify_on_topic_creation'] = True
		forum_res = adminapp.put_json(forum_location, forum_data)
		forum_ntiid = forum_res.json_body['NTIID']
		with mock_dataserver.mock_db_trans(self.ds):
			forum = find_object_with_ntiid(forum_ntiid)
			assert_that(forum, verifiably_provides(ISendEmailOnForumTypeCreation))

		# Test topic creation queues a job
		assert_that(queue.empty(), is_(True))
		self._POST_and_publish_topic_entry(forum_url=forum_location)
		assert_that(queue.empty(), is_not(True))

		# Test the number of emails sent matches the number of community members (fudge decorator does the assertion)
		job = queue.get()
		with mock_dataserver.mock_db_trans(self.ds):
			# In tests, we do not pickle the job, so we test that we can here.
			queue = ScheduledQueue('test_queue')
			queue._pickle(job)

			# We also want our job request to have an actual application_url
			actual_job = job._callable_root
			from pyramid.request import Request
			# We have to manually test this here since DummyRequest will not
			# build this out with an environ like an actual request would.
			mock_environ = environ_from_url(actual_job.job_kwargs['application_url'])
			mock_request = Request(mock_environ)
			assert_that(mock_request.application_url, is_('http://localhost'))
			# Need the db to resolve the topic ntiid in the job
			job()

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',), testapp=True)
	def test_community_admin_restricted_forum(self):
		self.default_origin = b'https://alpha.nextthought.com'
		with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
			self._create_user('basicuser', 'temp001', external_value={'realname': u'Basic User',
                                                                      'email': u'basic@user.com'})
			self._create_user('siteadmin', 'temp001', external_value={'realname': u'Site Admin',
																	  'email': u'siteadmin@user.com'})
			community = Community.get_community(self.default_community)
			set_entity_creation_site(community, 'alpha.nextthought.com')

		adminapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com'))
		forum_data = self._create_post_data_for_POST()

		# Create with it
		forum_data['admin_restricted'] = True
		forum_res = adminapp.post_json(self.board_pretty_url, forum_data, status=201)
		forum_location = forum_res.location
		forum_ntiid = forum_res.json_body['NTIID']
		with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
			forum = find_object_with_ntiid(forum_ntiid)
			assert_that(forum, verifiably_provides(ICommunityAdminRestrictedForum))

		# Disable via PUT
		forum_data['admin_restricted'] = False
		forum_res = adminapp.put_json(forum_location, forum_data)
		forum_ntiid = forum_res.json_body['NTIID']
		with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
			forum = find_object_with_ntiid(forum_ntiid)
			assert_that(forum, does_not(verifiably_provides(ICommunityAdminRestrictedForum)))

		# Enable via PUT
		forum_data['admin_restricted'] = True
		forum_res = adminapp.put_json(forum_location, forum_data)
		forum_ntiid = forum_res.json_body['NTIID']
		with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
			forum = find_object_with_ntiid(forum_ntiid)
			assert_that(forum, verifiably_provides(ICommunityAdminRestrictedForum))

		# Check basic user cannot create topics in forum
		testapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username='basicuser'))
		topic_data = self._create_post_data_for_POST()
		testapp.post_json(forum_location,
						  topic_data,
						  status=403)

		# Check nti admin still has privs
		adminapp.post_json(forum_location, topic_data, status=201)

		# Check site admins are forbidden on non site communities
		with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
			site = getSite()
			prm = IPrincipalRoleManager(site)
			prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, 'siteadmin')

		siteadminapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username='siteadmin'))
		siteadminapp.post_json(forum_location, topic_data)

		# Make basic user an admin
		adminapp.put_json('/dataserver2/users/%s/@@AddAdmin' % self.default_community,
						  {'usernames': 'basicuser'},
						  status=200)

		# Check basic user that is now an admin can create
		testapp.post_json(forum_location, topic_data, status=201)
