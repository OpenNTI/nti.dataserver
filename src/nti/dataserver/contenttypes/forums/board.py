#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions of boards.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import schema
from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.container.interfaces import INameChooser

from ZODB.interfaces import IConnection

from ExtensionClass import Base

from nti.containers.containers import AcquireObjectsOnReadMixin
from nti.containers.containers import AbstractNTIIDSafeNameChooser
from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.dataserver.contenttypes.forums import MessageFactory as _

from nti.dataserver.contenttypes.forums import _CreatedNamedNTIIDMixin
from nti.dataserver.contenttypes.forums import _CreatedIntIdNTIIDMixin

from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_DFL_BOARD
from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_COMMUNITY_BOARD

from nti.dataserver.contenttypes.forums.interfaces import IBoard
from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard
from nti.dataserver.contenttypes.forums.interfaces import IDFLForum
from nti.dataserver.contenttypes.forums.interfaces import IGeneralBoard
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard
from nti.dataserver.contenttypes.forums.interfaces import ICommunityForum
from nti.dataserver.contenttypes.forums.interfaces import IDefaultForumBoard

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.sharing import AbstractReadableSharedWithMixin

from nti.schema.fieldproperty import AdaptingFieldProperty

DEFAULT_BOARD_NAME = u'DiscussionBoard'


@interface.implementer(IBoard)
class Board(Base,
            AcquireObjectsOnReadMixin,
            CheckingLastModifiedBTreeContainer,
            AbstractReadableSharedWithMixin):

    __external_can_create__ = False
    __name__ = __default_name__ = DEFAULT_BOARD_NAME

    mimeType = None  # for static analysis; real value filled in by externalization

    title = AdaptingFieldProperty(IBoard['title'])
    description = AdaptingFieldProperty(IBoard['description'])

    ForumCount = property(CheckingLastModifiedBTreeContainer.__len__)

    sharingTargets = ()
    creator = None


@interface.implementer(IGeneralBoard)
class GeneralBoard(Board):
    __external_can_create__ = False

@interface.implementer(ICommunityBoard)
class NoDefaultForumCommunityBoard(GeneralBoard, _CreatedNamedNTIIDMixin):

    __external_can_create__ = False
    _ntiid_type = NTIID_TYPE_COMMUNITY_BOARD

@interface.implementer(IDefaultForumBoard, ICommunityBoard)
class CommunityBoard(NoDefaultForumCommunityBoard):
    
    def createDefaultForum(self):
        return ICommunityForum(self.creator)  # Ask the ICommunity

@interface.implementer(IDFLBoard)
class DFLBoard(GeneralBoard, _CreatedIntIdNTIIDMixin):
    __external_can_create__ = False
    _ntiid_type = NTIID_TYPE_DFL_BOARD

    def createDefaultForum(self):
        return IDFLForum(self.creator)  # Ask the DFL


def _prepare_annotation_board(clazz, iface, creator, title, name=None):
    board = clazz()
    board.__parent__ = creator
    board.creator = creator
    board.title = _(title)

    name = name or clazz.__default_name__
    annotations = IAnnotations(creator)
    annotations[name] = board

    jar = IConnection(creator, None)
    if jar:
        jar.add(board)
    errors = schema.getValidationErrors(iface, board)
    if errors:
        __traceback_info__ = errors
        raise errors[0][1]
    return board


def _adapt_fixed_board(owner, board_cls, board_iface, name=None):
    annotations = IAnnotations(owner)
    name = name or board_cls.__default_name__
    board = annotations.get(name)
    if board is None:
        board = _prepare_annotation_board(board_cls, board_iface, owner, name)
    return board


def AnnotatableBoardAdapter(context, board_impl_class, board_iface):
    """
    When a board is stored using annotations, this simplifies the process.
    """
    return _adapt_fixed_board(context, board_impl_class, board_iface)


@component.adapter(ICommunity)
@interface.implementer(ICommunityBoard)
def GeneralBoardCommunityAdapter(community):
    """
    For the moment, we will say that all communities have a single board, in the same
    way that all users have a blog. Only administrators can create forums
    within the board (with the exception of a single default, general
    purpose forum that always exists)
    """
    # TODO: Note the similarity to personalBlogAdapter
    return AnnotatableBoardAdapter(community, CommunityBoard, ICommunityBoard)


@interface.implementer(ICommunityBoard)
@component.adapter(IDynamicSharingTargetFriendsList)
def GeneralBoardDFLAdapter(dfl):
    """
    For the moment, we will say that all DFLs have a single board, in the same
    way that all users have a blog. DFL owners can create forums
    within the board
    """
    # TODO: Note the similarity to personalBlogAdapter
    return AnnotatableBoardAdapter(dfl, DFLBoard, IDFLBoard)


@component.adapter(IBoard)
@interface.implementer(INameChooser)
class BoardNameChooser(AbstractNTIIDSafeNameChooser):
    """
    Handles NTIID-safe name choosing for a forum in a board
    """
    leaf_iface = IBoard
