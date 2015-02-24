#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NTIID resolvers.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.ntiids import AbstractUserBasedResolver
from nti.dataserver.ntiids import AbstractAdaptingUserBasedResolver
from nti.dataserver.ntiids import AbstractMappingAdaptingUserBasedResolver

from nti.ntiids import ntiids
from nti.ntiids.ntiids import get_specific
from nti.ntiids import interfaces as nid_interfaces

from . import interfaces as frm_interfaces

@interface.implementer(nid_interfaces.INTIIDResolver)
class _BlogResolver(AbstractAdaptingUserBasedResolver):
	"""
	Resolves the one blog that belongs to a user, if one does exist.

	Register with the name :const:`.NTIID_TYPE_PERSONAL_BLOG`.
	"""

	required_iface = nti_interfaces.IUser
	adapt_to = frm_interfaces.IPersonalBlog

@interface.implementer( nid_interfaces.INTIIDResolver )
class _BlogEntryResolver(AbstractMappingAdaptingUserBasedResolver):
	"""
	Resolves a single blog entry within a user.

	Register with the name :const:`.NTIID_TYPE_PERSONAL_BLOG_ENTRY`.
	"""

	required_iface = nti_interfaces.IUser
	adapt_to = frm_interfaces.IPersonalBlog
	# because of this, __name__ of the entry must be NTIID safe

@interface.implementer(nid_interfaces.INTIIDResolver)
class _CommunityBoardResolver(AbstractAdaptingUserBasedResolver):
	"""
	Resolves the default board that belongs to a community, if one does exist.

	Register with the name :const:`.NTIID_TYPE_COMMUNITY_BOARD`
	"""

	required_iface = nti_interfaces.ICommunity
	adapt_to = frm_interfaces.ICommunityBoard

@interface.implementer(nid_interfaces.INTIIDResolver)
class _CommunityForumResolver(AbstractMappingAdaptingUserBasedResolver):
	"""
	Resolves a forum that belongs to a community.

	Register with the name :const:`.NTIID_TYPE_COMMUNITY_FORUM`
	"""

	required_iface = nti_interfaces.ICommunity
	adapt_to = frm_interfaces.ICommunityBoard # adapt to a board, look inside for a named forum

	def _resolve( self, ntiid, community ):
		forum = super(_CommunityForumResolver,self)._resolve( ntiid, community )
		if forum is None and ntiids.get_specific(ntiid) == 'Forum': # Hmm, is it the default?
			forum = frm_interfaces.ICommunityForum( community, None )
		return forum

@interface.implementer(nid_interfaces.INTIIDResolver)
class _CommunityTopicResolver(AbstractUserBasedResolver):
	"""
	Resolves a topic in the one forum that belongs to a community, if one does exist.

	Register with the name :const:`.NTIID_TYPE_COMMUNITY_TOPIC`
	"""

	required_iface = nti_interfaces.ICommunity
	adapt_to = frm_interfaces.ICommunityForum

	def _resolve( self, ntiid, community ):
		board = frm_interfaces.ICommunityBoard( community, None )
		if board is None:
			return None
		return resolve_ntiid_in_board(ntiid, board)

def resolve_forum_ntiid_in_board(ntiid, board):
	"""
	Finds a specific forum in a board,
	given an NTIID. Handles the naming conventions within the board.
	"""

	forum_name = get_specific(ntiid)
	return board.get( forum_name, {} )

def resolve_ntiid_in_board(ntiid, board):
	"""
	Finds a specific topic inside a specific forum in a board,
	given an NTIID. Handles the naming conventions within the board.
	"""

	specific = get_specific(ntiid)

	if '.' not in specific:
		forum_name, topic_name = specific, u''
		logger.warn("unexpected nttid specific part '%s' while resolving topic " % specific)
		return board.get( forum_name, {} ).get( topic_name )

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

	return board.get( forum_name, {} ).get( topic_name )
