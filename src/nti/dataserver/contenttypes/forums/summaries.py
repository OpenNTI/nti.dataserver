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

from zope.intid.interfaces import IIntIds

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

	def accumulate(self, comment):
		if not IDeletedObjectPlaceholder.providedBy( comment ):
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

	contexts = alias( 'Contexts' )
	user = alias( 'User' )
	nested_child_reply_count = alias( 'NestedChildReplyCount' )
	direct_child_reply_count = alias( 'DirectChildReplyCount' )

	def __init__(self, user):
		self.user = user
		self.contexts = []
		self.nested_child_reply_count = 0
		self.direct_child_reply_count = 0
		super(UserTopicParticipationSummary, self).__init__()

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

	def _recur_get_child_reply_count(self, comment):
		result = 0
		for child_reply in comment.replies:
			result += 1
			result += self._recur_get_child_reply_count( child_reply )
		return result

	def accumulate(self, comment):
		# For deleted comments, we include all spawned reply counts, but
		# exclude the rest.
		self.nested_child_reply_count += self._recur_get_child_reply_count( comment )
		self.direct_child_reply_count += len( comment.replies )
		# TODO: Do we need to de-dupe somehow...?
		# TODO: Or do need a set of all these...plus it seems
		# like we wanted to double count our replies (count all
		# nested replies plus all nested replies of a child comment
		# created by the same creator).
		self.contexts.append( UserTopicParticipationContext( comment ) )
		super(UserTopicParticipationSummary, self).accumulate( comment )
