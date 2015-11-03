#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from nti.appserver.workspaces.interfaces import IUserWorkspace
from nti.appserver.workspaces.interfaces import IContainerCollection

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener

from nti.dataserver.users.entity import Entity
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.externalization import externalization

from nti.links.links import Link

from nti.zodb import isBroken

@component.adapter(IUserWorkspace)
@interface.implementer(IContainerCollection)
class _UserBoardCollection(object):
	"""
	Turns a User into a ICollection of data for their boards.
	"""

	name = 'Boards'
	__name__ = name
	__parent__ = None

	accepts = ()
	container = ()

	def __init__(self, user_workspace):
		self.__parent__ = user_workspace

	@property
	def links(self):
		site = component.queryUtility(ICommunitySitePolicyUserEventListener)
		community_name = getattr(site, 'COM_USERNAME', None)
		community = Entity.get_entity(community_name)
		if community is not None and not isBroken(community):
			# We just want the user's community board.
			board = ICommunityBoard(community)
			board_ntiid = externalization.to_external_ntiid_oid(board)
			link = Link(board_ntiid, rel='global.site.board')
			link._name_ = 'global.site.board'
			return (link,)
		return ()

@component.adapter(IUserWorkspace)
@interface.implementer(IContainerCollection)
def _UserBoardCollectionFactory(workspace):
	return _UserBoardCollection(workspace)
