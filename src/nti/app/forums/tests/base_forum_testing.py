#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import ends_with
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import starts_with
from hamcrest import greater_than
from hamcrest import has_property
from hamcrest import contains_string
from hamcrest import is_not as does_not
from hamcrest import greater_than_or_equal_to
is_not = does_not

import datetime
import unittest
from urllib import quote as UQ

from pyquery import PyQuery

import webob.datetime_utils

import simplejson as json

from zope import lifecycleevent

from zope.component import eventtesting

from zope.intid.interfaces import IIntIdRemovedEvent

from zope.location.interfaces import ISublocations

from nti.testing.matchers import is_empty

from nti.testing.time import time_monotonically_increases

from nti.dataserver import users

from nti.ntiids import ntiids

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.application_webtest import AppTestBaseMixin

from nti.app.testing.base import TestBaseMixin

from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS

from nti.appserver.policies.tests import test_application_censoring

from nti.appserver.tests.test_application import TestApp as _TestApp

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

POST_MIME_TYPE = 'application/vnd.nextthought.forums.post'

def _plain(mt):
	return mt[:-5] if mt.endswith('+json') else mt

class UserCommunityFixture(object):

	def __init__(self, test, community_name='TheCommunity'):
		self.community_name = community_name
		self.ds = test.ds
		self.test = test
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(username='original_user@foo')
			user2 = self._create_user(username='user2@foo')
			user3 = self._create_user(username='user3@foo')
			user_following_2 = self._create_user(username='user_following_2@foo')
			user2_following_2 = self._create_user(username='user2_following_2@foo')

			# make them share a community
			community = users.Community.get_community(community_name, self.ds) or \
						users.Community.create_community(username=community_name)
			user.record_dynamic_membership(community)
			user2.record_dynamic_membership(community)
			user3.record_dynamic_membership(community)
			user_following_2.record_dynamic_membership(community)
			user2_following_2.record_dynamic_membership(community)

			user2.follow(user)
			user_following_2.follow(user2)
			user2_following_2.follow(user2)

			self.user2_username = user2.username
			self.user_username = user.username
			self.user3_username = user3.username
			self.user2_follower_username = user_following_2.username
			self.user2_follower2_username = user2_following_2.username


		self.testapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user_username))
		self.testapp2 = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user2_username))
		self.testapp3 = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user3_username))
		self.user2_followerapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user2_follower_username))
		self.user2_follower2app = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user2_follower2_username))

	def __getattr__(self, name):
		return getattr(self.test, name)

class AbstractPostCreationMixin(object):

	forum_pretty_url = None

	forum_comment_unique = 'UNIQUETOCOMMENT'

	forum_headline_class_type = 'Post'
	forum_headline_unique = 'UNIQUETOHEADLINE'
	forum_headline_content_type = POST_MIME_TYPE

	def _create_post_data_for_POST(self):
		unique = self.forum_headline_unique
		data = { 'Class': self.forum_headline_class_type,
				 'MimeType': self.forum_headline_content_type,
				 'title': 'My New Blog',
				 'description': "This is a description of the thing I'm creating",
				 'body': ['My first thought. ' + unique] }

		return data

	def _create_comment_data_for_POST(self):
		""" Always returns a plain Post so we can be sure that the correct Mime transformation happens. """
		unique = self.forum_comment_unique
		data = { 'Class': 'Post',
				 'title': 'A comment',
				 'body': ['This is a comment body ' + unique ] }
		return data

	def _POST_topic_entry(self, data=None, content_type=None, status_only=None, forum_url=None):
		testapp = self.testapp
		if data is None:
			data = self._create_post_data_for_POST()

		kwargs = {'status': 201}
		meth = testapp.post_json
		post_data = data
		if content_type:
			kwargs['headers'] = {b'Content-Type': str(content_type)}
			# testapp.post_json forces the content-type header
			meth = testapp.post
			post_data = json.dumps(data)
		if status_only:
			kwargs['status'] = status_only

		res = meth(forum_url or self.forum_pretty_url,
					 post_data,
					 **kwargs)

		return res

	def _POST_and_publish_topic_entry(self, data=None, forum_url=None):
		""" Returns (publish Response, topic data) """
		if data is None:
			data = self._create_post_data_for_POST()
		res = self._POST_topic_entry(data=data, forum_url=forum_url)

		publish_url = self.require_link_href_with_rel(res.json_body, 'publish')
		res = self.testapp.post(publish_url)
		return res, data

class AbstractTestApplicationForumsBase(AppTestBaseMixin, AbstractPostCreationMixin, TestBaseMixin):
	# : make nosetests only run subclasses of this that set __test__ to True
	__test__ = False

	default_username = 'original_user@foo'  # Not an admin user by default 'sjohnson@nextthought.com'
	default_entityname = default_username
	forum_ntiid = 'tag:nextthought.com,2011-10:' + default_username + '-Forum:PersonalBlog-Blog'
	forum_url_relative_to_user = 'Blog'
	forum_content_type = None

	forum_link_rel = None
	forum_title = default_username
	forum_type = None
	forum_topic_content_type = None
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:' + default_username + '-Topic:PersonalBlogEntry-'
	forum_topic_comment_content_type = None

	# Define these to get testing at the board level
	board_pretty_url = None
	board_link_rel = None
	board_ntiid = None
	board_ntiid_checker = None  # Set this to board_ntiid or something like not_none()
	board_content_type = None

	def setUp(self):
		super(AbstractTestApplicationForumsBase, self).setUp()
		self.forum_pretty_url = UQ('/dataserver2/users/' + self.default_entityname + '/' + self.forum_url_relative_to_user)
		if self.forum_ntiid:
			self.forum_ntiid_url = UQ('/dataserver2/NTIIDs/' + self.forum_ntiid)
		self.forum_pretty_contents_url = self.forum_pretty_url + '/contents'
		self.default_username_url = UQ('/dataserver2/users/' + self.default_username)
		self.default_username_pages_url = self.default_username_url + '/Pages'

	def forum_topic_ntiid(self, entryid):
		if self.forum_topic_ntiid_base:
			return self.forum_topic_ntiid_base + entryid

	def forum_topic_href(self, entryid):
		return self.forum_pretty_url + '/' + UQ(entryid)

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_entity_has_default_forum(self):
		testapp = self.testapp

		# The forum can be found at a pretty url, and by NTIID
		pretty_url = self.forum_pretty_url
		ntiid_url = self.forum_ntiid_url
		for url in pretty_url, ntiid_url:
			if not url:
				continue

			res = testapp.get(url)
			blog_res = res
			assert_that(res, has_property('content_type', self.forum_content_type))
			assert_that(res.json_body, has_entry('title', self.forum_title))
			if self.forum_ntiid:
				assert_that(res.json_body, has_entry('NTIID', self.forum_ntiid))

			# We have a contents URL
			contents_href = self.require_link_href_with_rel(res.json_body, 'contents')
			# Make sure we're getting back pretty URLs...
			assert_that(contents_href, starts_with(self.forum_pretty_contents_url))
			# which is empty...
			testapp.get(contents_href, status=200)

			# The forum cannot be liked, favorited, flagged
			self.forbid_link_with_rel(blog_res.json_body, 'like')
			self.forbid_link_with_rel(blog_res.json_body, 'flag')
			self.forbid_link_with_rel(blog_res.json_body, 'favorite')

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_cannot_POST_new_forum_entry_to_pages(self):
		testapp = self.testapp

		data = self._create_post_data_for_POST()

		# No containerId
		testapp.post_json(self.default_username_url, data, status=422)
		testapp.post_json(self.default_username_pages_url, data, status=422)

		data['ContainerId'] = 'tag:foo:bar'
		testapp.post_json(self.default_username_url, data, status=422)
		res = testapp.post_json(self.default_username_pages_url, data, status=422)

		# depending on how we implement ContainerId, we get different errors
		# assert_that( res.json_body, has_entry( 'code', 'InvalidContainerType' ) )
		# assert_that( res.json_body, has_entry( 'field', 'ContainerId' ) )

		assert_that(res.json_body, has_entry('code', 'InvalidContainerType'))
		assert_that(res.json_body, has_entry('field', 'containerId'))
		assert_that(res.json_body, has_entry('message', is_not(is_empty())))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_and_flagging_returns_same_href(self):
		data = self._create_post_data_for_POST()

		res = self._POST_topic_entry(data, status_only=201)

		assert_that(res.location, is_('http://localhost' + res.json_body['href'] + '/'))
		self.testapp.get(res.location)  # ensure it can be fetched from here

		topic_res = self.testapp.get(res.json_body['href'])  # as well as its internal href
		assert_that(topic_res.json_body, has_entry('title', data['title']))
		assert_that(topic_res.json_body, has_entry('MimeType', _plain(self.forum_topic_content_type)))
		topic_href = res.json_body['href']

		flag_href = self.require_link_href_with_rel(res.json_body, 'flag')
		res2 = self.testapp.post(flag_href)

		assert_that(res2.json_body['href'], is_(topic_href))
		self.require_link_href_with_rel(res2.json_body, 'flag.metoo')
		self.forbid_link_with_rel(res2.json_body, 'flag')

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_with_non_ascii_title(self):
		data = self._create_post_data_for_POST()
		# Give the title something non-Ascii
		data['title'] = 'Я ♥ борщ'  # ""I love borshch"" in Russian Cyrillic
		res = self._POST_topic_entry(data, status_only=201)

		assert_that(res.location, is_('http://localhost' + res.json_body['href'] + '/'))
		self.testapp.get(res.location)  # ensure it can be fetched from here

		topic_res = self.testapp.get(res.json_body['href'])  # as well as its internal href
		assert_that(topic_res.json_body, has_entry('title', data['title']))
		# The standard transliteration has been applied
		# if we're deriving NTIIDs that way
		if self.forum_ntiid:
			assert_that(topic_res.json_body, has_entry('NTIID', ends_with('ia_borshch')))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_header_only(self):
		data = self._create_post_data_for_POST()

		# With neither, but a content-type header
		del data['MimeType']
		del data['Class']

		self._do_test_user_can_POST_new_forum_entry(data, content_type=POST_MIME_TYPE)

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_class_only(self):
		data = self._create_post_data_for_POST()
		del data['MimeType']

		self._do_test_user_can_POST_new_forum_entry(data)


	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_mime_type_only(self):
		data = self._create_post_data_for_POST()
		del data['Class']
		self._do_test_user_can_POST_new_forum_entry(data)

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_uncensored_by_default(self):
		data = self._create_post_data_for_POST()
		data['title'] = test_application_censoring.bad_word
		data['body'] = [test_application_censoring.bad_val]
		self._do_test_user_can_POST_new_forum_entry(data)

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_resulting_in_blog_being_sublocation(self):
		# Creating a Blog causes it to be a sublocation of the entity
		# This way deleting/moving the user correctly causes the blog to be deleted/moved

		self._POST_topic_entry(self._create_post_data_for_POST())

		with mock_dataserver.mock_db_trans(self.ds):
			entity = users.Entity.get_entity(self.default_entityname)

			all_subs = dict()
			def _recur(i):
				all_subs[id(i)] = i
				subs = ISublocations(i, None)
				if subs:
					for x in subs.sublocations():
						_recur(x)
			_recur(entity)

			assert_that(all_subs.values(), has_item(is_(self.forum_type)))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_PUT_to_edit_existing_forum_topic_headline(self):

		testapp = self.testapp

		data = self._create_post_data_for_POST()
		res = self._POST_topic_entry(data)

		topic_url = res.location
		assert_that(topic_url, contains_string(self.forum_pretty_url))
		# I can PUT directly to the headline's edit URL
		headline_url = self.require_link_href_with_rel(res.json_body['headline'], 'edit')
		# Which is not 'pretty'
		assert_that(headline_url, contains_string('Objects'))

		data['body'] = ['An updated body']
		testapp.put_json(headline_url, data)

		# And check it by getting the whole container
		res = testapp.get(topic_url)
		assert_that(res.json_body, has_entry('headline', has_entry('body', data['body'])))

		# Changing the title changes the title of the container, but NOT the url or ID of anything
		data['title'] = 'A New Title'
		testapp.put_json(headline_url, data)
		res = testapp.get(topic_url)
		assert_that(res.json_body, has_entry('headline', has_entry('title', data['title'])))
		assert_that(res.json_body, has_entry('title', data['title']))

		# Pretty URL did not change
		testapp.get(topic_url)

		# I can also PUT to the pretty path to the headline
		data['body'] = ['An even newer body']

		testapp.put_json(topic_url + 'headline', data)
		res = testapp.get(topic_url)
		assert_that(res.json_body, has_entry('headline', has_entry('body', data['body'])))

		# And I can use the 'fields' URL to edit just parts of it, including title and body
		for field in 'body', 'title':
			data[field] = 'Edited with fields'
			if field == 'body': data[field] = [data[field]]

			testapp.put_json(headline_url + '/++fields++' + field, data[field])
			res = testapp.get(topic_url)
			assert_that(res.json_body, has_entry('headline', has_entry(field, data[field])))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	@time_monotonically_increases
	def test_creator_can_POST_new_comment(self):
		# """POSTing an IPost to the URL of an existing IStoryTopic adds a comment"""

		testapp = self.testapp

		# Create the topic
		res = self._POST_topic_entry()
		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']
		entry_mod_time = res.json_body['Last Modified']

		forum_res = testapp.get(self.forum_pretty_url)

		# (Same user) comments on blog by POSTing a new post
		data = self._create_comment_data_for_POST()

		res = testapp.post_json(entry_url, data, status=201)

		self._check_posted_comment(testapp, data, entry_url, entry_ntiid, entry_mod_time, res, forum_res)

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_can_be_sorted_by_post_count(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp

		# Create one topic
		topic_res1 = self._POST_topic_entry()
		entry_url = topic_res1.location
		# comment on it
		data = self._create_comment_data_for_POST()
		comment_res1 = testapp.post_json(entry_url, data, status=201)
		comment_res1.json_body['CreatedTime']

		# Create another topic
		res = self._POST_topic_entry()
		assert_that(res.location, is_not(entry_url))
		entry_url = res.location
		# comment on it
		data = self._create_comment_data_for_POST()
		comment_res2 = testapp.post_json(entry_url, data, status=201)
		comment_res2.json_body['CreatedTime']

		# And again
		data = self._create_comment_data_for_POST()
		comment_res2 = testapp.post_json(entry_url, data, status=201)
		comment_res2.json_body['CreatedTime']

		# And a topic with no comments
		self._POST_topic_entry()

		contents_res = testapp.get(	self.forum_pretty_contents_url,
									params={'sortOn': 'PostCount',
											'sortOrder': 'descending'})

		assert_that(contents_res.json_body, has_entry('Items', has_length(3)))
		assert_that(contents_res.json_body['Items'], contains(has_entry('PostCount', 2),
															  has_entry('PostCount', 1),
															  has_entry('PostCount', 0)))

		contents_res = testapp.get(	self.forum_pretty_contents_url,
									params={'sortOn': 'PostCount',
											'sortOrder': 'ascending'})

		assert_that(contents_res.json_body, has_entry('Items', has_length(3)))
		assert_that(contents_res.json_body['Items'], contains(has_entry('PostCount', 0),
															  has_entry('PostCount', 1),
															  has_entry('PostCount', 2)))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_can_be_sorted_by_comment_creation_date(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		# Create one topic
		topic_res1 = self._POST_topic_entry()
		entry_url = topic_res1.location
		# comment on it
		data = self._create_comment_data_for_POST()
		comment_res1 = testapp.post_json(entry_url, data, status=201)
		comment_ts1 = comment_res1.json_body['CreatedTime']

		# Create another topic
		res = self._POST_topic_entry()
		assert_that(res.location, is_not(entry_url))
		entry_url = res.location
		# comment on it
		data = self._create_comment_data_for_POST()
		comment_res2 = testapp.post_json(entry_url, data, status=201)
		comment_ts2 = comment_res2.json_body['CreatedTime']

		contents_res = testapp.get(self.forum_pretty_contents_url,
									params={'sortOn': 'NewestDescendantCreatedTime', 'sortOrder': 'descending'})
		orig_content_lm = contents_res.last_modified
		assert_that(contents_res.json_body, has_entry('Items', has_length(2)))
		assert_that(contents_res.json_body['Items'], contains(has_entry('NewestDescendantCreatedTime', comment_ts2),
															  has_entry('NewestDescendantCreatedTime', comment_ts1)))

		contents_res = testapp.get(self.forum_pretty_contents_url, params={'sortOn': 'NewestDescendantCreatedTime', 'sortOrder': 'ascending'})
		assert_that(contents_res.json_body, has_entry('Items', has_length(2)))
		assert_that(contents_res.json_body['Items'], contains(has_entry('NewestDescendantCreatedTime', comment_ts1),
															  has_entry('NewestDescendantCreatedTime', comment_ts2)))

		forum_res = testapp.get(self.forum_pretty_url)
		assert_that(forum_res.json_body, has_entry('NewestDescendant', has_entry('CreatedTime', comment_ts2)))

		# Of course, neither of these is visible to user2 yet...
		contents_res = testapp2.get(self.forum_pretty_contents_url)
		assert_that(contents_res.json_body, has_entry('Items', is_empty()))
		# ...and the new comment doesn't show up for this user, though
		# the timestamp (and sort order, should that matter) do. This should
		# be incredibly rare
		forum_res = testapp2.get(self.forum_pretty_url)
		assert_that(forum_res.json_body, has_entry('NewestDescendant', is_(none())))
		assert_that(forum_res.json_body, has_entry('NewestDescendantCreatedTime', comment_ts2))

		# The timestamp has been updated as well
		contents_res = testapp2.get(self.forum_pretty_contents_url)
		assert_that(contents_res.json_body['Last Modified'], is_(comment_ts2))
		assert_that(contents_res.last_modified, is_(greater_than_or_equal_to(orig_content_lm)))

		# If we add a topic that is newer and unpublished...
		self._POST_topic_entry()
		# this bumps the comment out of place
		forum_res = testapp2.get(self.forum_pretty_url)
		assert_that(forum_res.json_body, has_entry('NewestDescendant', is_(none())))

		# If I publish the first one...
		testapp.post(self.require_link_href_with_rel(topic_res1.json_body, 'publish'))
		# ...and ask for it as the other user, that's what I see
		forum_res = testapp2.get(self.forum_pretty_url)
		assert_that(forum_res.json_body, has_entry(	'NewestDescendant',
													 has_entries('href', topic_res1.json_body['href'],
																 'PublicationState', 'DefaultPublished')))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	@time_monotonically_increases
	def test_creator_can_POST_new_comment_to_contents(self):
		# By posting to /contents, we can get better client-side cache behaviour
		testapp = self.testapp

		# Create the topic
		res = self._POST_topic_entry()
		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']
		entry_mod_time = res.json_body['Last Modified']

		# (Same user) comments on blog by POSTing a new post
		data = self._create_comment_data_for_POST()

		contents_url = self.require_link_href_with_rel(res.json_body, 'contents')

		res = testapp.post_json(contents_url, data, status=201)

		self._check_posted_comment(testapp, data, entry_url, entry_ntiid, entry_mod_time, res)

	def _check_posted_comment(self, testapp, data, entry_url, entry_ntiid, entry_mod_time, comment_res, forum_res=None):

		assert_that(comment_res.status_int, is_(201))
		assert_that(comment_res.location, is_('http://localhost' + comment_res.json_body['href'] + '/'))

		def _check_comment_res(cres):
			assert_that(cres.json_body, has_entries('title', data['title'],
													'body', data['body'],
													'ContainerId', entry_ntiid))
			assert_that(cres.json_body, has_key('NTIID'))
			assert_that(cres, has_property('content_type', self.forum_topic_comment_content_type))

		_check_comment_res(comment_res)

		# Side effects: The container's PostCount is incremented
		res = testapp.get(entry_url)
		assert_that(res.json_body, has_entry('PostCount', 1))
		# And so is its mod time
		assert_that(res.json_body, has_entry('Last Modified', greater_than(entry_mod_time)))

		# The comment can be searched for
		search_res = self.search_user_rugd(self.forum_comment_unique)
		assert_that(search_res.json_body, has_entry('Hit Count', 1))
		assert_that(search_res.json_body, has_entry('Items', has_length(1)))
		assert_that(search_res.json_body['Items'][0], has_entry('ID', comment_res.json_body['ID']))

		# The comment can be fetched directly
		_check_comment_res(testapp.get(comment_res.location))
		# and by ntiid
		_check_comment_res(self.fetch_by_ntiid(comment_res.json_body['NTIID']))

		# None of this changed the modification time of the forum itself
		if forum_res is not None:
			forum_res_after_comment = testapp.get(self.forum_pretty_url)
			assert_that(forum_res_after_comment.last_modified, is_(forum_res.last_modified))
			assert_that(forum_res_after_comment.json_body['Last Modified'], is_(forum_res.json_body['Last Modified']))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	@time_monotonically_increases
	def test_creator_can_DELETE_comment_yielding_placeholders(self):
		testapp = self.testapp

		# Create the topic
		res = self._POST_topic_entry()
		entry_url = res.location
		entry_contents_url = self.require_link_href_with_rel(res.json_body, 'contents')
		# entry_ntiid = res.json_body['NTIID']

		data = self._create_comment_data_for_POST()
		res = testapp.post_json(entry_url, data, status=201)
		assert_that(res.status_int, is_(201))
		edit_url = self.require_link_href_with_rel(res.json_body, 'edit')
		entry_creation_time = res.json_body['Last Modified']
		orig_etag = testapp.get(self.require_link_href_with_rel(testapp.get(entry_url).json_body, 'contents')).etag
		testapp.get(entry_contents_url, headers={b'If-None-Match': orig_etag}, status=304)
		eventtesting.clearEvents()

		res = testapp.delete(edit_url)
		assert_that(res.status_int, is_(204))

		testapp.get(edit_url, status=404)
		res = self.testapp.get(entry_contents_url)
		__traceback_info__ = res.json_body
		self.require_link_href_with_rel(res.json_body['Items'][0], 'replies')

		# When it is replaced with placeholders
		res = testapp.get(entry_url)
		assert_that(res.json_body, has_entry('PostCount', 1))
		# and nothing was actually deleted yet
		del_events = eventtesting.getEvents(lifecycleevent.IObjectRemovedEvent)
		assert_that(del_events, has_length(0))
		assert_that(eventtesting.getEvents(IIntIdRemovedEvent), has_length(0))

		# But modification events did fire...
		mod_events = eventtesting.getEvents(lifecycleevent.IObjectModifiedEvent)
		assert_that(mod_events, has_length(1))
		# ...resulting in an updated time for the contents view
		res = testapp.get(entry_contents_url)
		assert_that(res.json_body['Last Modified'], is_(greater_than(entry_creation_time)))
		# ... and a changed href
		assert_that(self.require_link_href_with_rel(testapp.get(entry_url).json_body, 'contents'), is_not(entry_contents_url))
		# ... and a changed etag
		assert_that(res.etag, is_not(orig_etag))
		testapp.get(entry_contents_url, headers={b'If-None-Match': orig_etag}, status=200)

		# and the comment can no longer be found by search
		search_res = self.search_user_rugd(self.forum_comment_unique)
		assert_that(search_res.json_body, has_entry('Hit Count', 0))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_creator_can_DELETE_existing_empty_forum_topic(self):
		testapp = self.testapp

		res = self._POST_topic_entry()
		topic_url = res.location
		headline_url = self.require_link_href_with_rel(res.json_body['headline'], 'edit')

		eventtesting.clearEvents()

		res = testapp.delete(topic_url)
		assert_that(res.status_int, is_(204))

		res = testapp.get(self.forum_pretty_url)
		assert_that(res.json_body, has_entry('TopicCount', 0))
		testapp.get(topic_url, status=404)
		testapp.get(headline_url, status=404)

		# When the topic was deleted from the forum, it fired a single ObjectRemovedEvent.
		# This was dispatched to sublocations and refired, resulting
		# in intids being removed for the topic and the headline.
		# (TODO: This isn't symmetrical with ObjectAddedEvent; we get one for topic and headline,
		# right?)
		assert_that(eventtesting.getEvents(lifecycleevent.IObjectRemovedEvent), has_length(1))
		assert_that(eventtesting.getEvents(IIntIdRemovedEvent), has_length(2))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_creator_cannot_change_sharing_on__any_child(self):
		# """ Sharing is fixed and cannot be changed for a blog entry, its story, or a comment"""

		testapp = self.testapp
		res = self._POST_topic_entry()

		# topic_url = res.location
		headline_url = self.require_link_href_with_rel(res.json_body['headline'], 'edit')

		eventtesting.clearEvents()

		# Field updates
		# Cannot change the entry, if it is a community entry. If it is a blog entry, we can
		# testapp.put_json( topic_url + '/++fields++sharedWith',
		# 				  ['Everyone'],
		# 				  # Because of the way traversal is right now, this results in a 404,
		# 				  # when really we want a 403
		# 				  status=404)

		# Cannot change the story
		testapp.put_json(headline_url + '/++fields++sharedWith',
						  ['Everyone'],
						  status=404)  # same as above


		# Nor when putting the whole thing
		# The entry itself simply cannot be modified (predicate mismatch right now)
		# testapp.put_json( topic_url,
		# 				  {'sharedWith': ['Everyone']},
		# 				  status=404 )

		# The story accepts it but ignores it
		res = testapp.put_json(headline_url,
								{'sharedWith': ['Everyone']},
								status=200)
		assert_that(res.json_body, has_entry('sharedWith', is_empty()))

		res = testapp.get(headline_url)
		assert_that(res.json_body, has_entry('sharedWith', is_empty()))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_creator_can_publish_topic_simple_visible_to_other_user_in_community(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		# First user creates the topic
		data = self._create_post_data_for_POST()
		topic_data = data.copy()

		# Create the blog
		res = self._POST_topic_entry(topic_data)
		topic_url = res.location
		# topic_ntiid = res.json_body['NTIID']
		topic_entry_id = res.json_body['ID']
		self.require_link_href_with_rel(res.json_body, 'contents')
		self.require_link_href_with_rel(res.json_body['headline'], 'edit')

		publish_url = self.require_link_href_with_rel(res.json_body, 'publish')

		# Before its published, the second user can see nothing
		res = testapp2.get(self.forum_pretty_contents_url)
		assert_that(res.json_body['Items'], has_length(0))
		content_last_mod = res.json_body['Last Modified']
		assert_that(res.last_modified, is_(datetime.datetime.fromtimestamp(content_last_mod, webob.datetime_utils.UTC)))

		res = testapp2.get(self.forum_pretty_url)
		assert_that(res.json_body, has_entry('TopicCount', 0))

		# When it is published...
		testapp.post(publish_url)

		# Second user is able to see everything about it...
		def assert_shared_with_community(data):
			if self.check_sharedWith_community:
				assert_that(data, has_entry('sharedWith', contains('TheCommunity')))

		# ...Its entry in the table-of-contents...
		res = testapp2.get(self.forum_pretty_url)
		assert_that(res.json_body, has_entry('TopicCount', 1))

		# ...Its full entry...
		res = testapp2.get(self.forum_pretty_contents_url)
		__traceback_info__ = self.forum_pretty_contents_url
		assert_that(res.json_body['Items'][0], has_entry('title', topic_data['title']))
		assert_that(res.json_body['Items'][0], has_entry('headline', has_entry('body', topic_data['body'])))
		assert_shared_with_community(res.json_body['Items'][0])
		# ...Which has an updated last modified...
		assert_that(res.json_body['Last Modified'], greater_than(content_last_mod))
		content_last_mod = res.json_body['Last Modified']
		assert_that(res.last_modified, is_(datetime.datetime.fromtimestamp(content_last_mod, webob.datetime_utils.UTC)))

		# ...It can be fetched by pretty URL...
		res = testapp2.get(self.forum_topic_href(topic_entry_id))
		assert_that(res, has_property('content_type', self.forum_topic_content_type))
		assert_that(res.json_body, has_entry('title', topic_data['title']))
		assert_that(res.json_body, has_entry('ID', topic_entry_id))
		assert_that(res.json_body, has_entry('headline', has_entry('body', topic_data['body'])))
		assert_shared_with_community(res.json_body)

		# XXX contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		# XXX self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel(res.json_body, 'flag')  # entries can be flagged

		# ...It can be fetched directly...
		testapp2.get(topic_url)

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_published_topic_is_in_activity(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, data = self._POST_and_publish_topic_entry()

		# ...It can be seen in the activity stream for the author by the author and the people it
		# is shared with ...
		for app in testapp, testapp2:
			res = self.fetch_user_activity(app, self.default_username)
			assert_that(res.json_body, has_entry('Items',
												  # Expecting exactly one match, the topic
												  contains(has_entries('title', data['title']))))

		# Until it is unpublished,
		testapp.post(self.require_link_href_with_rel(publish_res.json_body, 'unpublish'))
		# When it is still in my activity
		res = self.fetch_user_activity(testapp, self.default_username)
		assert_that(res.json_body['Items'], contains(has_entry('title', data['title'])))
		# but not the other users view of my activity
		res = self.fetch_user_activity(testapp2, self.default_username)
		assert_that(res.json_body['Items'], does_not(contains(has_entry('title', data['title']))))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_published_topic_is_in_feed(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		parent_url = self.forum_pretty_url
		feed_url = parent_url + '/feed.atom'

		# ...It can be seen in the feed for the author by the author and the people it
		# is shared with ...
		for app in testapp, testapp2:
			res = app.get(feed_url)
			assert_that(res.content_type, is_('application/atom+xml'))

			# lxml is a tightass and refuses to parse Unicode strings that
			# contain a xml declaration of an encoding (raises ValueError).
			# Yet webtest insists on passing the unicode body to the parser,
			# and of course it carries an encoding. So we strip it here
			assert_that(res.text, contains_string('<?xml version="1.0" encoding="utf-8"?>\n'))
			res.text = res.text[len('<?xml version="1.0" encoding="utf-8"?>\n'):]
			xml = res.lxml

			assert_that(xml.xpath('//atom:entry/atom:summary/text()', namespaces={'atom':"http://www.w3.org/2005/Atom"}),
						contains(contains_string(self.forum_headline_unique)))

		# Until it is unpublished,
		testapp.post(self.require_link_href_with_rel(publish_res.json_body, 'unpublish'))
		# When it is still in my feed
		res = testapp.get(feed_url)
		assert_that(res.text, contains_string(self.forum_headline_unique))
		# but not the other users feed
		res = testapp2.get(feed_url)
		assert_that(res.text, does_not(contains_string(self.forum_headline_unique)))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_published_topic_is_in_activity_until_DELETEd(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, data = self._POST_and_publish_topic_entry()

		# ...It can be seen in the activity stream for the author by the author and the people it
		# is shared with ...
		for app in testapp, testapp2:
			res = self.fetch_user_activity(app, self.default_username)
			assert_that(res.json_body['Items'], contains(has_entry('title', data['title'])))

		# Until it is deleted
		testapp.delete(publish_res.location)
		# When it is no longer anywhere
		for app in testapp, testapp2:
			res = self.fetch_user_activity(app, self.default_username)
			assert_that(res.json_body['Items'], does_not(contains(has_entry('title', data['title']))))
			# In fact the activity is empty
			assert_that(res.json_body['Items'], is_empty())

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_published_topic_is_in_rstream_until_DELETEd(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, data = self._POST_and_publish_topic_entry()

		# ...It can be seen in the recursive stream for the people
		# is shared with ...
		for app, uname in (# (testapp, fixture.user_username),
						   (testapp2, fixture.user2_username),):
			res = self.fetch_user_root_rstream(app, uname)
			assert_that(res.json_body['Items'], contains(has_entry('Item', has_entry('title', data['title']))))

		# Until it is deleted
		testapp.delete(publish_res.location)
		# When it is no longer anywhere
		for app, uname in (# (testapp, fixture.user_username),
						   (testapp2, fixture.user2_username),):
			res = self.fetch_user_root_rstream(app, uname, status=404)

	check_sharedWith_community = True

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_can_comment_in_published_topic(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location
		content_href = self.require_link_href_with_rel(publish_res.json_body, 'contents')

		# non-creator can comment
		comment_data = self._create_comment_data_for_POST()
		comment_res = testapp2.post_json(topic_url, comment_data, status=201)
		assert_that(comment_res, has_property('content_type', self.forum_topic_comment_content_type))
		if self.check_sharedWith_community:
			assert_that(comment_res.json_body, has_entry('sharedWith', [fixture.community_name]))
		self.require_link_href_with_rel(comment_res.json_body, 'edit')
		self.require_link_href_with_rel(comment_res.json_body, 'flag')
		self.require_link_href_with_rel(comment_res.json_body, 'favorite')
		self.require_link_href_with_rel(comment_res.json_body, 'like')
		replies_link = self.require_link_href_with_rel(comment_res.json_body, 'replies')

		# This affected the count and contents as well
		self._check_comment_in_topic_contents(testapp, topic_url, comment_data, fixture)

		for app in testapp, testapp2:
			self._check_comment_in_topic_feed(app, topic_url, comment_data)

		act_res = testapp.get('/dataserver2/users/' + fixture.user2_username + '/Activity')
		assert_that(act_res.json_body['Items'], contains(has_entry('title', comment_data['title'])))

		# And the contents link
		new_content_href = self.require_link_href_with_rel(self.testapp.get(topic_url).json_body, 'contents')
		assert_that(new_content_href, is_not(content_href))

		# The non-creator can also reply to that one
		reply_data = self._create_comment_data_for_POST()
		reply_data['inReplyTo'] = comment_res.json_body['NTIID']
		reply_data['references'] = [comment_res.json_body['NTIID']]
		reply_res = testapp2.post_json(topic_url, reply_data, status=201)
		assert_that(reply_res.json_body, has_entry('inReplyTo', comment_res.json_body['NTIID']))

		new_comment_res = testapp2.get(comment_res.json_body['href'])
		assert_that(new_comment_res.json_body, has_entry('ReferencedByCount', 1))

		reply_content_href = self.require_link_href_with_rel(self.testapp.get(topic_url).json_body, 'contents')
		assert_that(reply_content_href, is_not(new_content_href))

		# We can fetch the contents to get just the TopLevel objects
		content_res = self.testapp.get(reply_content_href, params={'filter': 'TopLevel'})
		assert_that(content_res.json_body, has_entry('Items', has_length(1)))
		assert_that(content_res.json_body['Items'][0], has_entry('OID', comment_res.json_body['OID']))

		# We can fetch the replies directly too
		replies_res = self.testapp.get(replies_link)
		assert_that(replies_res.json_body, has_entry('Items', has_length(1)))
		assert_that(replies_res.json_body['Items'][0], has_entry('OID', reply_res.json_body['OID']))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_can_favorite_topic(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, data = self._POST_and_publish_topic_entry()
		# topic_ntiid = publish_res.json_body['NTIID']
		topic_cnt_id = publish_res.json_body['ContainerId']
		fav_href = self.require_link_href_with_rel(publish_res.json_body, 'favorite')

		testapp2.post(fav_href)
		res = self.fetch_user_root_rugd(testapp2, fixture.user2_username, params={'filter': 'Favorite'})
		assert_that(res.json_body['Items'], contains(has_entry('title', data['title'])))
		unfav_href = self.require_link_href_with_rel(res.json_body['Items'][0], 'unfavorite')
		with mock_dataserver.mock_db_trans(self.ds):
			# Check where it is stored
			user2 = users.User.get_user(fixture.user2_username)
			shared_cont = user2.getSharedContainer(topic_cnt_id)
			assert_that(shared_cont, has_length(1))

		# Can be cycled
		testapp2.post(unfav_href)
		res = self.fetch_user_root_rugd(testapp2, fixture.user2_username, params={'filter': 'Favorite'})
		assert_that(res.json_body, has_entry('FilteredTotalItemCount', 0))
		assert_that(res.json_body['Items'], is_empty())


		testapp2.post(fav_href)
		res = self.fetch_user_root_rugd(testapp2, fixture.user2_username, params={'filter': 'Favorite'})
		assert_that(res.json_body['Items'], contains(has_entry('title', data['title'])))

		# If the creator deletes it, it is well and truly gone
		testapp.delete(publish_res.location)
		res = self.fetch_user_root_rugd(testapp2, fixture.user2_username, params={'filter': 'Favorite'})
		assert_that(res.json_body['Items'], is_empty())

		with mock_dataserver.mock_db_trans(self.ds):
			user2 = users.User.get_user(fixture.user2_username)
			shared_cont = user2.getSharedContainer(topic_cnt_id)
			assert_that(list(shared_cont), is_empty())

	def _check_comment_in_topic_contents(self, testapp, topic_url, comment_data, fixture):
		res = testapp.get(topic_url)
		assert_that(res.json_body, has_entry('PostCount', 1))
		res = testapp.get(self.require_link_href_with_rel(res.json_body, 'contents'))
		# Should be well cached... see comments in views about why this is disabled
		# assert_that( res.cache_control, has_property( 'max_age', 3600 ) )
		assert_that(res.cache_control, has_property('max_age', 0))
		comment_data.pop('Class', None)  # don't compare, it changes
		if self.check_sharedWith_community:
			comment_data['sharedWith'] = [fixture.community_name]

		assert_that(res.json_body['Items'], has_length(1))
		assert_that(res.json_body['Items'][0], has_entries(comment_data))

	def _check_comment_in_topic_feed(self, testapp, topic_url, comment_data):
		res = testapp.get(topic_url + '/feed.atom')
		assert_that(res.content_type, is_('application/atom+xml'))
		res._use_unicode = False
		pq = PyQuery(res.body,
					  parser='html',  # html to ignore namespaces. Sigh.
					  namespaces={u'atom': u'http://www.w3.org/2005/Atom'})

		titles = sorted([x.text for x in pq(b'entry title')])
		sums = sorted([x.text for x in pq(b'entry summary')])
		assert_that(titles, contains(comment_data['title']))
		assert_that(sums, contains('<div><br />' + comment_data['body'][0] + '</div>'))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_can_edit_comment_in_published_topic(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location
		contents_href = self.require_link_href_with_rel(testapp.get(topic_url).json_body, 'contents')

		# non-creator can comment
		comment_data = self._create_comment_data_for_POST()
		comment_res = testapp2.post_json(topic_url, comment_data, status=201)
		edit_href = self.require_link_href_with_rel(comment_res.json_body, 'edit')
		# which changes the contents href
		new_contents_href = self.require_link_href_with_rel(testapp.get(topic_url).json_body, 'contents')
		assert_that(new_contents_href, is_not(contents_href))
		contents_href = new_contents_href

		# (Stash the topic last mod time after adding the comment)
		topic_last_mod = testapp.get(topic_url).json_body['Last Modified']

		# Now edit the comment
		comment_data['title'] = 'Changed my title'
		comment_data['body'] = ["Different comment body"]
		del comment_data['Class']  # don't compare, it changes

		comment_res = testapp2.put_json(edit_href, comment_data)

		if self.check_sharedWith_community:
			comment_data['sharedWith'] = [fixture.community_name]
		assert_that(comment_res.json_body, has_entries(comment_data))

		self._check_comment_in_topic_contents(testapp, topic_url, comment_data, fixture)
		for app in testapp, testapp2:
			self._check_comment_in_topic_feed(app, topic_url, comment_data)

		# and editing changed the contents link
		new_contents_href = self.require_link_href_with_rel(testapp.get(topic_url).json_body, 'contents')
		assert_that(new_contents_href, is_not(contents_href))

		# And the last mod time of the topic
		assert_that(testapp.get(topic_url).json_body, has_entry('Last Modified', greater_than(topic_last_mod)))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_comment_can_be_flagged(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location

		# non-creator can comment
		comment_data = self._create_comment_data_for_POST()
		comment_res = testapp2.post_json(topic_url, comment_data, status=201)

		res = testapp.post(self.require_link_href_with_rel(comment_res.json_body, 'flag'))
		assert_that(res.json_body['href'], is_(comment_res.json_body['href']))
		self.require_link_href_with_rel(res.json_body, 'flag.metoo')

	@WithSharedApplicationMockDS
	def test_post_canvas_image_in_headline_post_produces_fetchable_link(self):
		fixture = UserCommunityFixture(self)
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		canvas_data = {u'Class': 'Canvas',
					   u'ContainerId': 'tag:foo:bar',
					   u'MimeType': u'application/vnd.nextthought.canvas',
					   'shapeList': [{u'Class': 'CanvasUrlShape',
									  u'MimeType': u'application/vnd.nextthought.canvasurlshape',
									  u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}

		data = self._create_post_data_for_POST()
		data['body'].append(canvas_data)

		# Create the blog
		res = self._POST_topic_entry(data)
		topic_ntiid = res.json_body['NTIID']
		pub_url = self.require_link_href_with_rel(res.json_body, 'publish')

		def _check_canvas(res, canvas, acc_to_other=False):
			assert_that(canvas, has_entry('shapeList', has_length(1)))
			assert_that(canvas, has_entry('shapeList', contains(has_entry('Class', 'CanvasUrlShape'))))
			assert_that(canvas, has_entry('shapeList', contains(has_entry('url', contains_string('/dataserver2/')))))

			res = testapp.get(canvas['shapeList'][0]['url'])
			# The content type is preserved
			assert_that(res, has_property('content_type', 'image/gif'))
			# The modified date is the same as the canvas containing it
			assert_that(res, has_property('last_modified', not_none()))
		# 	assert_that( res, has_property( 'last_modified', canvas_res.last_modified ) )
			# It either can or cannot be accessed by another user
			testapp2.get(canvas['shapeList'][0]['url'], status=(200 if acc_to_other else 403))

		_check_canvas(res, res.json_body['headline']['body'][1])

		# If we "edit" the headline, then nothing breaks
		headline_edit_link = self.require_link_href_with_rel(res.json_body['headline'], 'edit')

		res = testapp.put_json(headline_edit_link, res.json_body['headline'])
		_check_canvas(res, res.json_body['body'][1])

		with mock_dataserver.mock_db_trans(self.ds):
			__traceback_info__ = topic_ntiid
			topic = ntiids.find_object_with_ntiid(topic_ntiid)
			assert_that(topic, is_(not_none()))
			canvas = topic.headline.body[1]
			url_shape = canvas.shapeList[0]
			# And it externalizes as a real link because it owns the file data
			assert_that(url_shape.toExternalObject()['url'], ends_with('@@view'))

		# When published, it is visible to the other user
		testapp.post(pub_url)
		_check_canvas(res, res.json_body['body'][1], acc_to_other=True)

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_normal_user_cannot_post_to_board(self):
		if not self.board_pretty_url:
			raise unittest.SkipTest('No board url')
		# attempting to do so gets you DENIED
		self.testapp.post_json(self.board_pretty_url, self._create_post_data_for_POST(), status=403)

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',), testapp=True)
	def test_super_user_can_post_to_board_to_create_forum(self):
		if not self.board_pretty_url:
			raise unittest.SkipTest('No board url')

		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com'))
		forum_data = self._create_post_data_for_POST()
		# Incoming mimetype is actually unimportant at this point
		del forum_data['Class']
		del forum_data['MimeType']
		forum_res = adminapp.post_json(self.board_pretty_url, forum_data, status=201)

		# Which creates a forum
		assert_that(forum_res, has_property('content_type', self.forum_content_type))
		forum_url = self.board_pretty_url + '/' + forum_res.json_body['ID']
		assert_that(forum_res.json_body, has_entry('href', forum_url))
		assert_that(forum_res, has_property('location', 'http://localhost' + forum_url + '/'))
		assert_that(forum_res.json_body, has_entry('ContainerId', self.board_ntiid_checker))
		self.require_link_href_with_rel(forum_res.json_body, 'edit')
		assert_that(forum_res.json_body, has_entry('title', forum_data['title']))
		assert_that(forum_res.json_body, has_entry('description', forum_data['description']))

	def _get_board_href_via_rel(self):
		# default board has a contents href which can be fetched,
		# returning the default forum
		community = self.resolve_user(username=self.default_community)
		board_href = self.require_link_href_with_rel(community, self.board_link_rel)
		return board_href

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_default_board_contents(self):
		if not self.board_pretty_url:
			raise unittest.SkipTest('No board url')

		board_href = self._get_board_href_via_rel()
		assert_that(board_href, is_(self.board_pretty_url))

		board_res = self.testapp.get(board_href)
		assert_that(board_res, has_property('content_type', self.board_content_type))
		assert_that(board_res.json_body, has_entry('MimeType', _plain(self.board_content_type)))
		assert_that(board_res.json_body, has_entry('NTIID', self.board_ntiid_checker))
		assert_that(board_res.json_body, has_entry('href', self.board_pretty_url))
		__traceback_info__ = board_res.json_body
		contents_href = self.require_link_href_with_rel(board_res.json_body, 'contents')
		add = self.link_with_rel(board_res.json_body, 'add')
		if add is not None:
			assert_that(add, has_entry('method', 'POST'))
			assert_that(contents_href, is_(add['href']))

		contents_res = self.testapp.get(contents_href)
		assert_that(contents_res.json_body, has_entry('Items', has_length(1)))
		assert_that(contents_res.json_body['Items'][0], has_entry('MimeType', _plain(self.forum_content_type)))

	def _do_simple_tests_for_POST_of_topic_entry(self, data, content_type=None, status_only=None, expected_data=None):
		res = self._POST_topic_entry(data, content_type=content_type, status_only=status_only)
		if status_only:
			return res

		# Returns the representation of the new topic created
		data = expected_data or data
		assert_that(res, has_property('content_type', self.forum_topic_content_type))
		assert_that(res.json_body, has_entry('ID', ntiids.make_specific_safe(data['title'])))
		entry_id = res.json_body['ID']
		assert_that(entry_id, is_(not_none()))
		board_id = res.json_body['BoardNTIID']
		assert_that(board_id, is_(not_none()))
		assert_that(res.json_body, has_entries(	'title', data['title'],
												'href', self.forum_topic_href(entry_id)))

		ntiid = self.forum_topic_ntiid(entry_id)
		if ntiid:
			assert_that(res.json_body, has_entry('NTIID', ntiid))
		if self.forum_ntiid:
			assert_that(res.json_body, has_entry('ContainerId', self.forum_ntiid))

		assert_that(res.json_body['headline'], has_entries(	'title', data['title'],
															'body', data['body']))

		self.require_link_href_with_rel(res.json_body, 'contents')
		self.require_link_href_with_rel(res.json_body, 'like')  # entries can be liked
		self.require_link_href_with_rel(res.json_body, 'flag')  # entries can be flagged
		self.require_link_href_with_rel(res.json_body, 'edit')  # entries can be 'edited' (actually they cannot, shortcut for ui)
		self.require_link_href_with_rel(res.json_body, 'favorite')  # entries can be favorited

		# The headline cannot be any of those things
		headline_json = res.json_body['headline']
		self.forbid_link_with_rel(headline_json, 'like')
		self.forbid_link_with_rel(headline_json, 'flag')
		self.forbid_link_with_rel(headline_json, 'favorite')

		# The entry can be fetched by NTIID
		if 'NTIID' in res.json_body:
			assert_that(self.fetch_by_ntiid(res.json_body['NTIID']).json_body,
						has_entry('NTIID', res.json_body['NTIID']))

		return res

	_do_test_user_can_POST_new_forum_entry = _do_simple_tests_for_POST_of_topic_entry

AbstractTestApplicationForumsBaseMixin = AbstractTestApplicationForumsBase
