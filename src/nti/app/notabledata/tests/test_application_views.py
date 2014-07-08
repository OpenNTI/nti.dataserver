#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_

from hamcrest import has_entry
from hamcrest import has_item

from hamcrest import has_length
from hamcrest import greater_than
from hamcrest import contains

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS
from urllib import unquote
from datetime import datetime

from nti.dataserver import users
from nti.dataserver import contenttypes
from nti.contentrange import contentrange
from nti.ntiids import ntiids
from nti.externalization.oids import to_external_ntiid_oid

from nti.dataserver.tests import mock_dataserver

from nti.testing.time import time_monotonically_increases
from nti.testing.matchers import is_true

from nti.externalization.internalization import update_from_external_object

from zope import component
from zope import interface
from zope import lifecycleevent
from ..interfaces import IUserNotableData
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard
from nti.dataserver.interfaces import IDeletedObjectPlaceholder

class TestApplicationNotableUGDQueryViews(ApplicationLayerTest):

	def _check_notable_data(self, username=None, length=1):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user(username)

			nd = component.getMultiAdapter((user,None), IUserNotableData)
			assert_that( nd, has_length( length ))
			for o in nd:
				assert_that( nd.is_object_notable(o), is_true() )

	@WithSharedApplicationMockDS(users=('jason'),
								 testapp=True,
								 default_authenticate=True)
	@time_monotonically_increases
	def test_notable_ugd_reply_to_me(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			jason = self._get_user('jason')

			# Note that we index normalized to the minute, so we need to give
			# these substantially different created times
			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n_containerId = top_n.containerId = u'tag:nti:foo'
			top_n.body = ("Top",)
			top_n.createdTime = 100
			user.addContainedObject( top_n )

			reply_n = contenttypes.Note()
			reply_n.applicableRange = contentrange.ContentRangeDescription()
			reply_n.containerId = u'tag:nti:foo'
			reply_n.body = ('Reply',)
			reply_n.inReplyTo = top_n
			reply_n.addReference(top_n)
			reply_n.createdTime = 200
			reply_n.lastModified = 1395693508

			jason.addContainedObject( reply_n )


			reply_ext_ntiid = to_external_ntiid_oid( reply_n )

			reply_n = contenttypes.Note()
			reply_n.applicableRange = contentrange.ContentRangeDescription()
			reply_n.containerId = u'tag:nti:foo'
			reply_n.body = ('Reply2',)
			reply_n.inReplyTo = top_n
			reply_n.addReference(top_n)
			reply_n.createdTime = 300
			jason.addContainedObject( reply_n )

			reply2_ext_ntiid = to_external_ntiid_oid( reply_n )

		path = '/dataserver2/users/%s/Pages(%s)/RUGDByOthersThatIMightBeInterestedIn/' % ( self.extra_environ_default_user, ntiids.ROOT )
		res = self.testapp.get(path)
		assert_that( res.last_modified.replace(tzinfo=None), is_( datetime.utcfromtimestamp(1395693508)))
		assert_that( res.json_body, has_entry( 'lastViewed', 0))
		assert_that( res.json_body, has_entry( 'TotalItemCount', 2))
		assert_that( res.json_body, has_entry( 'Items', has_length(2) ))
		# They are sorted descending by time by default
		assert_that( res.json_body, has_entry( 'Items',
											   contains(has_entry('NTIID', reply2_ext_ntiid),
														has_entry('NTIID', reply_ext_ntiid))))

		# We can sort ascending if we want
		res = self.testapp.get(path, params={'sortOrder': 'ascending'})
		assert_that( res.json_body, has_entry( 'Items',
											   contains(has_entry('NTIID', reply_ext_ntiid),
														has_entry('NTIID', reply2_ext_ntiid))))

		# We can limit the batch to a time range if we want
		res = self.testapp.get(path, params={'batchBefore': 299})
		assert_that( res.json_body, has_entry( 'Items',
											   contains(has_entry('NTIID', reply_ext_ntiid) ) ) )

		# We can update the lastViewed time

		lv_href = self.require_link_href_with_rel(res.json_body, 'lastViewed')
		assert_that(unquote(lv_href), is_(path + 'lastViewed') )
		self.testapp.put_json( lv_href,
							   1234 )
		res = self.testapp.get(path)
		assert_that( res.json_body, has_entry( 'lastViewed', greater_than(0)))
		lv = res.json_body['lastViewed']

		res = self.testapp.get(lv_href)
		assert_that( int(res.body), is_(lv) )
		self.testapp.put_json( lv_href,
							   1234 )
		res = self.testapp.get(lv_href)
		assert_that( int(res.body), is_(greater_than(lv) ) )


		self._check_notable_data(length=2)

	@WithSharedApplicationMockDS(users=('jason'),
								 testapp=True,
								 default_authenticate=True)
	@time_monotonically_increases
	def test_notable_ugd_top_level_shared_directly_to_me(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			jason = self._get_user('jason')

			# Note that we index normalized to the minute, so we need to give
			# these substantially different created times

			# Create two top level notes, one shared to me and one not,
			# as well as a reply to the one shared to me; we should only
			# find the top-level note shared with me notable
			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n.containerId = u'tag:nti:foo'
			top_n.body = ("Top",)
			top_n.createdTime = 100
			jason.addContainedObject( top_n )

			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n.containerId = u'tag:nti:foo'
			top_n.body = ("Top2",)
			top_n.createdTime = 100
			top_n.addSharingTarget(user)
			jason.addContainedObject( top_n )


			reply_n = contenttypes.Note()
			reply_n.applicableRange = contentrange.ContentRangeDescription()
			reply_n.containerId = u'tag:nti:foo'
			reply_n.body = ('Reply',)
			reply_n.inReplyTo = top_n
			reply_n.addReference(top_n)
			reply_n.createdTime = 200
			reply_n.addSharingTarget(user)
			jason.addContainedObject( reply_n )


			top_ext_ntiid = to_external_ntiid_oid( top_n )


		path = '/dataserver2/users/%s/Pages(%s)/RUGDByOthersThatIMightBeInterestedIn' % ( self.extra_environ_default_user, ntiids.ROOT )
		res = self.testapp.get(path)
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1))
		assert_that( res.json_body, has_entry( 'Items', has_length(1) ))
		# They are sorted descending by time by default
		assert_that( res.json_body, has_entry( 'Items',
											   contains(has_entry('NTIID', top_ext_ntiid))))

		self._check_notable_data()


	@WithSharedApplicationMockDS(users=('jason'),
								 testapp=True,
								 default_authenticate=True)
	@time_monotonically_increases
	def test_notable_ugd_blog_shared_directly_to_me(self):
		res = self.testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog',
									  {'Class': 'Post', 'title': 'my title', 'body': ['my body']},
									  status=201 )
		# Sharing is currently a two-step process
		self.testapp.put_json(res.json_body['href'], {'sharedWith': ['jason']})

		res = self.fetch_user_recursive_notable_ugd( username='jason',
													 extra_environ=self._make_extra_environ(username='jason') )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1))
		assert_that( res.json_body, has_entry( 'Items', has_length(1) ))
		assert_that( res.json_body, has_entry( 'Items',
											   contains(has_entry('Class', 'PersonalBlogEntry')) ) )

		self._check_notable_data(username='jason')


	def _setup_community(users_map):
		community = users.Community.create_community( username='TheCommunity' )
		for user in users_map.values():
			user.record_dynamic_membership(community)

	@WithSharedApplicationMockDS(users=('jason'),
								 testapp=True,
								 default_authenticate=True,
								 users_hook=_setup_community)
	@time_monotonically_increases
	def test_notable_toplevel_comments_in_forum_i_create(self):
		forum_url = '/dataserver2/users/TheCommunity/DiscussionBoard/Forum'

		post_data = { 'Class': 'Post',
				 #'MimeType': self.forum_headline_content_type,
				 'title': 'My New Blog',
				 'description': "This is a description of the thing I'm creating",
				 'body': ['My first thought. '] }

		res = self.testapp.post_json( forum_url, post_data )
		publish_url = self.require_link_href_with_rel( res.json_body, 'publish' )
		res = self.testapp.post( publish_url )


		self.testapp.post_json(res.location, {'Class': 'Post', 'body': ['A comment']},
							   extra_environ=self._make_extra_environ(username='jason'))

		res = self.fetch_user_recursive_notable_ugd( )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1))
		assert_that( res.json_body, has_entry( 'Items', has_length(1) ))
		assert_that( res.json_body, has_entry( 'Items',
											   contains(has_entry('body', ['A comment'])) ) )

		self._check_notable_data()

		# Now we can turn it off too
		with mock_dataserver.mock_db_trans(self.ds):
			com = users.Community.get_community('TheCommunity', self.ds)
			board = ICommunityBoard(com)
			forum = board['Forum']
			topic = list(forum.values())[0]

			user = users.User.get_user('sjohnson@nextthought.com')
			data = component.getMultiAdapter((user,None),
											 IUserNotableData)
			data.object_is_not_notable(topic)

		res = self.fetch_user_recursive_notable_ugd( )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 0))


	def _do_test_notable_ugd_tagged_to_entity(self, tag_name=None, initial_count=0):
		# Before it's shared with me, I can't see it, even
		# though it's tagged to me
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			jason = self._get_entity('jason')

			top_n = contenttypes.Note()
			top_n.applicableRange = contentrange.ContentRangeDescription()
			top_n.containerId = u'tag:nti:foo'
			top_n.body = ("Top",)
			top_n.createdTime = 100
			top_n.tags = contenttypes.Note.tags.fromObject([tag_name or user.NTIID])
			jason.addContainedObject( top_n )

			ext_ntiid = to_external_ntiid_oid( top_n )
			top_n_id = top_n.id

		path = '/dataserver2/users/%s/Pages(%s)/RUGDByOthersThatIMightBeInterestedIn' % ( self.extra_environ_default_user, ntiids.ROOT )
		res = self.testapp.get(path)
		assert_that( res.json_body, has_entry( 'TotalItemCount', initial_count))
		assert_that( res.json_body, has_entry( 'Items', has_length(initial_count) ))


		# Now I share it indirectly with me. The sharing is indirect
		# to verify we hit on the tagged property, not the sharedWith property
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			jason = self._get_user('jason')

			community = users.Community.create_community( self.ds, username='MathCounts' )
			user.record_dynamic_membership( community )
			jason.record_dynamic_membership( community )

			top_n = jason.getContainedObject( 'tag:nti:foo', top_n_id )

			update_from_external_object( top_n, {'sharedWith': ['MathCounts']}, context=self.ds)

		res = self.testapp.get(path)
		assert_that( res.json_body, has_entry( 'TotalItemCount', initial_count + 1))
		assert_that( res.json_body, has_entry( 'Items', has_length(initial_count + 1) ))

		assert_that( res.json_body, has_entry( 'Items',
											   has_item(has_entry('NTIID',ext_ntiid))))

		self._check_notable_data(length=initial_count+1)

		# If we mark it deleted, it is no longer notable
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			jason = self._get_user('jason')

			top_n = jason.getContainedObject( 'tag:nti:foo', top_n_id )
			interface.alsoProvides(top_n, IDeletedObjectPlaceholder)
			lifecycleevent.modified(top_n)

		res = self.testapp.get(path)
		assert_that( res.json_body, has_entry( 'TotalItemCount', initial_count))
		assert_that( res.json_body, has_entry( 'Items', has_length(initial_count) ))


	@WithSharedApplicationMockDS(users=('jason'),
								 testapp=True,
								 default_authenticate=True)
	@time_monotonically_increases
	def test_notable_ugd_tagged_to_me(self):
		self._do_test_notable_ugd_tagged_to_entity()


	@WithSharedApplicationMockDS(users=('jason'),
								 testapp=True,
								 default_authenticate=True)
	@time_monotonically_increases
	def test_notable_ugd_tagged_to_dfl(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			jason = self._get_user('jason')

			dfl = users.DynamicFriendsList( username='Friends' )
			dfl.creator = jason
			jason.addContainedObject( dfl )
			dfl.addFriend( user )
			dfl_ntiid = dfl.NTIID

			# Manually clear out the notable for the circled event
			#user._circled_events_intids_storage.clear()

		self._do_test_notable_ugd_tagged_to_entity(dfl_ntiid, initial_count=1)

	@WithSharedApplicationMockDS(users=('jason'),
								 testapp=True,
								 default_authenticate=True)
	@time_monotonically_increases
	def test_notable_ugd_circled(self):

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			jason = self._get_user('jason')

			user.accept_shared_data_from(jason)

		path = '/dataserver2/users/%s/Pages(%s)/RUGDByOthersThatIMightBeInterestedIn' % ( self.extra_environ_default_user, ntiids.ROOT )
		res = self.testapp.get(path)
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1))
		assert_that( res.json_body, has_entry( 'Items',
											   contains( has_entry( 'ChangeType', 'Circled' ))))

		self._check_notable_data()
		stream_res = self.fetch_user_root_rstream()

		assert_that( stream_res.json_body, has_entry( 'Items',
													  contains(has_entry('RUGDByOthersThatIMightBeInterestedIn', is_true()))))
