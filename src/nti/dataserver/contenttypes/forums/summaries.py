#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for forums.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import nameparser

from zope import component
from zope import interface

from nti.dataserver.interfaces import IDeletedObjectPlaceholder

from nti.dataserver.contenttypes.forums.interfaces import ITopicParticipationSummary
from nti.dataserver.contenttypes.forums.interfaces import IUserTopicParticipationContext
from nti.dataserver.contenttypes.forums.interfaces import IUserTopicParticipationSummary

from nti.dataserver.interfaces import IUsernameSubstitutionPolicy

from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.property.property import alias
from nti.property.property import Lazy

@interface.implementer(IUserTopicParticipationContext)
class UserTopicParticipationContext(object):

	def __init__(self, comment):
		self.Context = comment
		self.ParentContext = comment.inReplyTo

@interface.implementer(ITopicParticipationSummary)
class TopicParticipationSummary(object):

	comment_total_count = alias( 'TotalCount' )
	comment_top_level_count = alias( 'TopLevelCount' )
	comment_reply_to_count = alias( 'ReplyToCount' )

	def __init__(self):
		self.comment_total_count = 0
		self.comment_top_level_count = 0
		self.comment_reply_to_count = 0

	def _allow_comment(self, comment):
		return not IDeletedObjectPlaceholder.providedBy( comment )

	def accumulate(self, comment):
		if self._allow_comment( comment ):
			self.comment_total_count += 1
			if comment.inReplyTo is not None:
				self.comment_reply_to_count += 1
			else:
				self.comment_top_level_count += 1

def replace_username(username):
	substituter = component.queryUtility(IUsernameSubstitutionPolicy)
	if substituter is None:
		return username
	result = substituter.replace(username) or username
	return result

@interface.implementer(IUserTopicParticipationSummary)
class UserTopicParticipationSummary(TopicParticipationSummary):
	"""
	XXX: Currently, we count user self-replies in the count.
	"""

	contexts = alias( 'Contexts' )
	user = alias( 'User' )
	direct_child_reply_count = alias( 'DirectChildReplyCount' )

	def __init__(self, user):
		self.user = user
		self.contexts = []
		self._nested_replies = set()
		self.direct_child_reply_count = 0
		super(UserTopicParticipationSummary, self).__init__()

	@property
	def NestedChildReplyCount(self):
		return len( self._nested_replies )

	@Lazy
	def alias(self):
		named_user = IFriendlyNamed(self.user)
		return named_user.alias

	@Lazy
	def last_name(self):
		username = self.user.username
		profile = IUserProfile(self.user)

		lastname = ''
		realname = profile.realname or ''
		if realname and '@' not in realname and realname != username:
			human_name = nameparser.HumanName(realname)
			lastname = human_name.last or ''
		return lastname

	@Lazy
	def username(self):
		"""
		The displayable, sortable username.
		"""
		username = self.user.username
		return replace_username(username)

	def _recur_replies(self, comment):
		for child_reply in comment.replies:
			# Exclude from our count, but still recursively gather
			# the children.
			if self._allow_comment( child_reply ):
				self._nested_replies.add(child_reply)
			self._recur_replies( child_reply )

	def _get_direct_reply_count(self, comment):
		return len([x for x in comment.replies if self._allow_comment(x)])

	def accumulate(self, comment):
		# For deleted comments, we include all (non deleted) spawned reply
		# counts, but exclude the other stats.
		self._recur_replies( comment )
		self.direct_child_reply_count += self._get_direct_reply_count( comment )
		self.contexts.append( UserTopicParticipationContext( comment ) )
		super(UserTopicParticipationSummary, self).accumulate( comment )
