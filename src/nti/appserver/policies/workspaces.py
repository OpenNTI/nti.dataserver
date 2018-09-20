#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.appserver.workspaces.interfaces import IUserWorkspace
from nti.appserver.workspaces.interfaces import IContainerCollection

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver.users.communities import Community

from nti.ntiids.oids import to_external_ntiid_oid

from nti.links.links import Link

from nti.zodb import isBroken

logger = __import__('logging').getLogger(__name__)


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
        community = Community.get_community(community_name)
        if community is not None and not isBroken(community):
            # We just want the user's community board.
            board = ICommunityBoard(community)
            board_ntiid = to_external_ntiid_oid(board)
            # pylint: disable=protected-access
            link = Link(board_ntiid, rel='global.site.board')
            link._name_ = 'global.site.board'
            return (link,)
        return ()


@component.adapter(IUserWorkspace)
@interface.implementer(IContainerCollection)
def _UserBoardCollectionFactory(workspace):
    return _UserBoardCollection(workspace)
