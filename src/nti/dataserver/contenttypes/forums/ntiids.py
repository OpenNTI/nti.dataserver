#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTIID resolvers.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard
from nti.dataserver.contenttypes.forums.interfaces import IDFLForum
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard
from nti.dataserver.contenttypes.forums.interfaces import ICommunityForum

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.ntiids import AbstractUserBasedResolver
from nti.dataserver.ntiids import AbstractAdaptingUserBasedResolver
from nti.dataserver.ntiids import AbstractMappingAdaptingUserBasedResolver

from nti.ntiids.ntiids import get_provider
from nti.ntiids.ntiids import get_specific
from nti.ntiids.interfaces import INTIIDResolver

@interface.implementer(INTIIDResolver)
class _BlogResolver(AbstractAdaptingUserBasedResolver):
	"""
	Resolves the one blog that belongs to a user, if one does exist.

	Register with the name :const:`.NTIID_TYPE_PERSONAL_BLOG`.
	"""

	required_iface = IUser
	adapt_to = IPersonalBlog

@interface.implementer(INTIIDResolver)
class _BlogEntryResolver(AbstractMappingAdaptingUserBasedResolver):
	"""
	Resolves a single blog entry within a user.

	Register with the name :const:`.NTIID_TYPE_PERSONAL_BLOG_ENTRY`.
	"""

	required_iface = IUser
	adapt_to = IPersonalBlog
	# because of this, __name__ of the entry must be NTIID safe

@interface.implementer(INTIIDResolver)
class _CommunityBoardResolver(AbstractAdaptingUserBasedResolver):
	"""
	Resolves the default board that belongs to a community, if one does exist.

	Register with the name :const:`.NTIID_TYPE_COMMUNITY_BOARD`
	"""

	required_iface = ICommunity
	adapt_to = ICommunityBoard

@interface.implementer(INTIIDResolver)
class _CommunityForumResolver(AbstractMappingAdaptingUserBasedResolver):
	"""
	Resolves a forum that belongs to a community.

	Register with the name :const:`.NTIID_TYPE_COMMUNITY_FORUM`
	"""

	required_iface = ICommunity
	adapt_to = ICommunityBoard  # adapt to a board, look inside for a named forum

	def _resolve(self, ntiid, community):
		forum = super(_CommunityForumResolver, self)._resolve(ntiid, community)
		if forum is None and get_specific(ntiid) == 'Forum':  # Hmm, is it the default?
			forum = ICommunityForum(community, None)
		return forum

@interface.implementer(INTIIDResolver)
class _CommunityTopicResolver(AbstractUserBasedResolver):
	"""
	Resolves a topic in the one forum that belongs to a community, if one does exist.

	Register with the name :const:`.NTIID_TYPE_COMMUNITY_TOPIC`
	"""

	required_iface = ICommunity
	adapt_to = ICommunityForum

	def _resolve(self, ntiid, community):
		board = ICommunityBoard(community, None)
		if board is None:
			return None
		return resolve_ntiid_in_board(ntiid, board)

class _DFLResolverMixin(AbstractAdaptingUserBasedResolver):

	def resolve(self, ntiid):
		entity = None
		provider_name = get_provider(ntiid)
		intids = component.queryUtility(IIntIds)
		if intids is not None:
			provider_name = int(provider_name)
			entity = intids.queryObject(provider_name)
		if entity and self.required_iface.providedBy(entity):
			return self._resolve(ntiid, entity)

@interface.implementer(INTIIDResolver)
class _DFLBoardResolver(_DFLResolverMixin):
	"""
	Resolves the default board that belongs to a DFL, if one does exist.

	Register with the name :const:`.NTIID_TYPE_DFL_BOARD`
	"""

	adapt_to = IDFLBoard
	required_iface = IDynamicSharingTargetFriendsList

@interface.implementer(INTIIDResolver)
class _DFLForumResolver(_DFLResolverMixin):
	"""
	Resolves a forum that belongs to a DFL.

	Register with the name :const:`.NTIID_TYPE_DFL_FORUM`
	"""

	adapt_to = IDFLBoard  # adapt to a board, look inside for a named forum
	required_iface = IDynamicSharingTargetFriendsList

	def _resolve(self, ntiid, dfl):
		forum = super(_DFLForumResolver, self)._resolve(ntiid, dfl)
		if forum is None and get_specific(ntiid) == 'Forum':  # Hmm, is it the default?
			forum = IDFLForum(dfl, None)
		return forum

@interface.implementer(INTIIDResolver)
class _DFLTopicResolver(_DFLResolverMixin):
	"""
	Resolves a topic in the one forum that belongs to a DFL, if one does exist.

	Register with the name :const:`.NTIID_TYPE_DFL_TOPIC`
	"""

	adapt_to = IDFLForum
	required_iface = IDynamicSharingTargetFriendsList

	def _resolve(self, ntiid, dfl):
		board = IDFLBoard(dfl, None)
		if board is None:
			return None
		return resolve_ntiid_in_board(ntiid, board)

def resolve_forum_ntiid_in_board(ntiid, board):
	"""
	Finds a specific forum in a board,
	given an NTIID. Handles the naming conventions within the board.
	"""

	forum_name = get_specific(ntiid)
	return board.get(forum_name, {})

def resolve_ntiid_in_board(ntiid, board):
	"""
	Finds a specific topic inside a specific forum in a board,
	given an NTIID. Handles the naming conventions within the board.
	"""

	specific = get_specific(ntiid)

	if '.' not in specific:
		forum_name, topic_name = specific, u''
		logger.warn("unexpected nttid specific part '%s' while resolving topic " % specific)
		return board.get(forum_name, {}).get(topic_name)

	# Unfortunately, we use the . as both the NameChooser-unique
	# portion separator and the parent/child separator (we can't
	# change this because there may be existing iPad data
	# depending on this). Depending on which parts got uniqued, we
	# may need to adjust the split.
	# TODO: Is there still a case this could miss? If the IDs are just right?
	names = specific.split('.')
	if len(names) == 2:
		# Unambiguous
		forum_name, topic_name = names
	elif len(names) == 3:
		# Two dots, have to figure out which is parent/child and
		# which is unique. This depends on our implementation
		# of making names unique using numeric suffixes
		if names[1].isdigit():
			forum_name = names[0] + '.' + names[1]
			topic_name = names[2]
		else:
			forum_name = names[0]
			topic_name = names[1] + '.' + names[2]
	else:
		assert len(names) == 4
		# unambiguous case
		forum_name = names[0] + '.' + names[1]
		topic_name = names[2] + '.' + names[3]

	return board.get(forum_name, {}).get(topic_name)
