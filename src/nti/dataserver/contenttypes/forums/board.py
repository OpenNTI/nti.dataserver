#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions of boards.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import schema
from zope import interface
from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.container.interfaces import INameChooser

from ZODB.interfaces import IConnection

from nti.dataserver import sharing
from nti.dataserver import containers
from nti.dataserver.interfaces import ICommunity

from nti.schema.fieldproperty import AdaptingFieldProperty

from nti.utils._compat import Base

from .interfaces import IBoard
from .interfaces import IGeneralBoard
from .interfaces import ICommunityBoard
from .interfaces import ICommunityForum
from .interfaces import NTIID_TYPE_COMMUNITY_BOARD

from . import _CreatedNamedNTIIDMixin

@interface.implementer(IBoard)
class Board(Base,
			containers.AcquireObjectsOnReadMixin,
			containers.CheckingLastModifiedBTreeContainer,
			sharing.AbstractReadableSharedWithMixin):

	__external_can_create__ = False
	__name__ = __default_name__ = 'DiscussionBoard'
	mimeType = None  # for static analysis; real value filled in by externalization

	title = AdaptingFieldProperty(IBoard['title'])
	description = AdaptingFieldProperty(IBoard['description'])

	ForumCount = property(containers.CheckingLastModifiedBTreeContainer.__len__)

	sharingTargets = ()
	creator = None

@interface.implementer(IGeneralBoard)
class GeneralBoard(Board):
	__external_can_create__ = False

@interface.implementer(ICommunityBoard)
class CommunityBoard(GeneralBoard, _CreatedNamedNTIIDMixin):
	__external_can_create__ = False
	_ntiid_type = NTIID_TYPE_COMMUNITY_BOARD

	def createDefaultForum(self):
		return ICommunityForum(self.creator)  # Ask the ICommunity

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

@interface.implementer(ICommunityBoard)
@component.adapter(ICommunity)
def GeneralBoardCommunityAdapter(community):
	"""
	For the moment, we will say that all communities have a single board, in the same
	way that all users have a blog. Only administrators can create forums
	within the board (with the exception of a single default, general
	purpose forum that always exists)
	"""
	# TODO: Note the similarity to personalBlogAdapter
	return AnnotatableBoardAdapter(community, CommunityBoard, ICommunityBoard)

@component.adapter(IBoard)
@interface.implementer(INameChooser)
class BoardNameChooser(containers.AbstractNTIIDSafeNameChooser):
	"""
	Handles NTIID-safe name choosing for a forum in a board
	"""
	leaf_iface = IBoard
