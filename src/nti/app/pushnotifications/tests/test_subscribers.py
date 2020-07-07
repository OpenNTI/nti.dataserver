#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import quopri

import fudge

from hamcrest import contains_string
from hamcrest import is_
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that

from pyramid.threadlocal import get_current_request

from zope import component
from zope import interface

from nti.app.pushnotifications.subscribers import _is_user_online
from nti.app.pushnotifications.subscribers import user_mention_emailer

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.contentfragments.interfaces import PlainTextContentFragment

from nti.dataserver.interfaces import IStreamChangeEvent
from nti.dataserver.interfaces import StreamChangeAcceptedByUser

from nti.dataserver.users import users
from nti.dataserver.users import Community

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver.contenttypes.forums.post import GeneralForumComment

from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.testing import ITestMailDelivery


class TestSubscribers(ApplicationLayerTest):

	@staticmethod
	def _add_community_topic(creator,
							 forum,
							 topic_name,
							 request=None,
							 mentions=None,
							 post=None):
		topic = CommunityHeadlineTopic()
		topic.title = u'a test'
		topic.creator = creator

		if request is not None:
			request.remote_user = creator
			request.context = topic

		if post:
			if post.title:
				topic.title = post.title
			else:
				post.title = topic.title

			post.__parent__ = topic
			topic.headline = post

		if mentions:
			topic.mentions = mentions
			post.mentions = mentions

		forum[topic_name] = topic

		return topic

	def _add_comment(self,
					 creator,
					 topic,
					 body=None,
					 inReplyTo=None,
					 request=None,
					 mentions=()):
		comment = GeneralForumComment()
		comment.creator = creator
		comment.mentions = mentions
		if inReplyTo:
			comment.inReplyTo = inReplyTo

		if body:
			comment.body = body

		if request is not None:
			request.remote_user = creator
			request.context = comment

		topic[topic.generateId(prefix=u'comment')] = comment
		return comment

	@WithSharedApplicationMockDS(users=False, testapp=True, default_authenticate=False)
	@fudge.patch("nti.app.pushnotifications.subscribers._mailer",
				 "nti.app.pushnotifications.subscribers._is_subscribed")
	def test_threadable_added(self, mock_mailer, mock_is_subscribed):
		class _MockMailer(object):
			_calls = []
			def queue_simple_html_text_email(self, template_name, subject, recipients, template_args, reply_to, package, text_template_extension):
				self._calls.append((template_name, subject, recipients, reply_to, text_template_extension, template_args))

			def reset(self):
				del self._calls[:]

		_mockMailer = _MockMailer()
		mock_mailer.is_callable().returns(_mockMailer)
		mock_is_subscribed.is_callable().returns(True)

		with mock_dataserver.mock_db_trans(self.ds):
			community = Community.create_community(self.ds, username=u"test_demo")
			user1 = self._create_user(username=u'forum_owner', external_value={'email': u'forum_owner@example.com'})
			user2 = self._create_user(username=u'topic_owner', external_value={'email': u'topic_owner@example.com'})
			user3 = self._create_user(username=u'comment_user1', external_value={'email': u'comment_user1@example.com'})
			user4 = self._create_user(username=u'comment_user2', external_value={'email': u'comment_user2@example.com'})
			user5 = self._create_user(username=u"comment_user3")
			for _user in (user1, user2, user3, user4, user5):
				_user.record_dynamic_membership(community)

			board = ICommunityBoard(community)
			forum = board[u'Forum']

			topic = self._add_community_topic(user2, forum, u'Hello')
			topic.publish()

			named = IFriendlyNamed(user4)
			named.alias = u'user4'
			named.realname = u'Comment User4'

			# Top comment
			comment1 = self._add_comment(user3, topic, inReplyTo=None)
			assert_that(_mockMailer._calls, has_length(0))

			# Same creator with the creator of inReplyTo
			self._add_comment(user3, topic, inReplyTo=comment1)
			assert_that(_mockMailer._calls, has_length(0))

			mock_is_subscribed.is_callable().returns(False)
			comment3 = self._add_comment(user4, topic, inReplyTo=comment1)
			assert_that(_mockMailer._calls, has_length(0))

			mock_is_subscribed.is_callable().returns(None)
			self._add_comment(user4, topic, inReplyTo=comment1)
			assert_that(_mockMailer._calls, has_length(0))

			# Don't send if the author is mentioned, as we
			# currently prefer that notification
			mock_is_subscribed.is_callable().returns(True)
			mentions = PlainTextContentFragment(user3.username),
			self._add_comment(user4, topic, inReplyTo=comment1, mentions=mentions)
			assert_that(_mockMailer._calls, has_length(0))

			# Success
			mock_is_subscribed.is_callable().returns(True)
			self._add_comment(user4, topic, inReplyTo=comment1)
			assert_that(_mockMailer._calls, has_length(1))
			assert_that(_mockMailer._calls[0][0], is_('nti.app.pushnotifications:templates/digest_email'))
			assert_that(_mockMailer._calls[0][1], is_('Your NextThought Updates'))
			assert_that(_mockMailer._calls[0][2], is_([user3]))
			assert_that(_mockMailer._calls[0][3], is_(None))
			assert_that(_mockMailer._calls[0][4], is_('.mak'))
			assert_that(_mockMailer._calls[0][5], has_entries({ 'total_found': 1,
																'display_name': 'comment_user1',
																'site_name': 'Example',
																'notable_text': 'A user has replied to one of your comments.',
																'email_to': 'comment_user1@example.com (comment_user1)'}))

			self._add_comment(user3, topic, inReplyTo=comment3)
			assert_that(_mockMailer._calls, has_length(2))
			assert_that(_mockMailer._calls[1][2], is_([user4]))
			assert_that(_mockMailer._calls[1][5], has_entries({ 'total_found': 1,
																'display_name': 'user4',
																'site_name': 'Example',
																'notable_text': 'A user has replied to one of your comments.',
																'email_to': 'comment_user2@example.com (comment_user2)'}))

			_mockMailer.reset()

			# Top comment other
			self._add_comment(user5, topic, inReplyTo=None)
			assert_that(_mockMailer._calls, has_length(0))

	@mock_dataserver.WithMockDSTrans
	@fudge.patch("nti.dataserver.activitystream.hasQueryInteraction",
				 "nti.app.pushnotifications.subscribers._is_user_online",
				 "nti.app.pushnotifications.subscribers._is_subscribed")
	def test_mention_email(self, mock_interaction, is_online, is_subscribed):
		mock_interaction.is_callable().with_args().returns(True)
		is_online.is_callable().returns(True)
		is_subscribed.is_callable().returns(False)

		community = Community.create_community(self.ds, username=u"test_demo")
		user = users.User.create_user(self.ds, username=u'jason.madden@nextthought.com')
		bojangles = users.User.create_user(self.ds, username=u'bojangles@nextthought.com')
		mouse_user = users.User.create_user(self.ds, username=u'mmouse@nextthought.com')
		for _user in (user, mouse_user, bojangles):
			_user.record_dynamic_membership(community)

		profile = IUserProfile(user)
		profile.email = u'jason.madden@nextthought.com'
		profile.realname = u'Steve'

		board = ICommunityBoard(community)
		forum = board[u'Forum']

		topic = self._add_community_topic(user, forum, u'Hello')
		topic.publish()

		mailer = component.getUtility(ITestMailDelivery)

		# With no mentionable, nothing happens
		change = MockChange()
		event = StreamChangeAcceptedByUser(change, user)
		user_mention_emailer(event)
		assert_that(mailer.queue, has_length(0))

		# User not mentioned, nothing happens
		request = get_current_request()
		mentions = PlainTextContentFragment(u"bojangles@nextthought.com"),
		comment = self._add_comment(mouse_user, topic, request=request, mentions=mentions)
		assert_that(comment.isMentionedDirectly(user), is_(False))
		assert_that(mailer.queue, has_length(0))

		# User online, nothing happens
		mentions += PlainTextContentFragment(u"jason.madden@nextthought.com"),
		comment = self._add_comment(mouse_user, topic, request=request, mentions=mentions)
		assert_that(comment.isMentionedDirectly(user), is_(True))
		assert_that(mailer.queue, has_length(0))

		# User not subscribed, nothing happens
		is_online.is_callable().returns(False)
		comment = self._add_comment(mouse_user, topic, request=request, mentions=mentions)
		assert_that(comment.isMentionedDirectly(user), is_(True))
		assert_that(mailer.queue, has_length(0))

		# User mentioned, not online, and subscribed, mail sent
		is_subscribed.returns(True)
		request = get_current_request()
		body_text = u"0123456789" * 26
		body = (body_text,)
		self._add_comment(mouse_user, topic, body=body, request=request,
						  mentions=mentions)
		assert_that(mailer.queue, has_length(1))
		assert_that(_decode_message(mailer.queue[0]),
					contains_string("%s..." % (body_text[:250],)))

		# Sent with no body
		self._add_comment(mouse_user, topic, request=request,
						  mentions=mentions)
		assert_that(mailer.queue, has_length(2))
		assert_that(_decode_message(mailer.queue[1]),
					contains_string("in \"a test\"\n\n"))

		# Sent with body of headline post from headline topic

		# TypeError: Can't pickle objects in acquisition wrappers.
		# post = CommunityHeadlinePost()
		# post.body = body
		# topic = self._add_community_topic(mouse_user, forum, u'Topic 2',
		# 								  request=request, post=post,
		# 								  mentions=mentions)
		# topic.publish()
		# assert_that(mailer.queue, has_length(3))
		# assert_that(_decode_message(mailer.queue[2]),
		# 			contains_string("%s..." % (body_text[:250],)))

	@fudge.patch("nti.app.pushnotifications.subscribers._get_dataserver")
	def test_is_user_online_exception(self, get_ds):
		sessions = fudge.Fake("sessions").provides("get_sessions_by_owner").raises(KeyError())
		mock_ds = fudge.Fake("dataserver").has_attr(sessions=sessions)
		get_ds.is_callable().returns(mock_ds)
		assert_that(_is_user_online(mock_ds), is_(False))


def _decode_message(message):
	msg = quopri.decodestring(message.body)
	return msg.decode('utf-8', errors='ignore')


@interface.implementer(IStreamChangeEvent)
class MockChange(object):
	type = "Type"
	object = None
