#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions of boards.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import interface
from zope import component
from zope import schema

from zope.annotation import interfaces as an_interfaces
from . import interfaces as for_interfaces
from nti.dataserver import interfaces as nti_interfaces
from ZODB.interfaces import IConnection

from ._compat import Base

from nti.dataserver import containers
from nti.dataserver import sharing

from nti.utils.schema import AdaptingFieldProperty


@interface.implementer(for_interfaces.IBoard)
class Board(Base,
			containers.AcquireObjectsOnReadMixin,
			containers.CheckingLastModifiedBTreeContainer,
			sharing.AbstractReadableSharedWithMixin):

	__external_can_create__ = False
	__name__ = __default_name__ = 'DiscussionBoard'

	title = AdaptingFieldProperty(for_interfaces.IBoard['title'])
	description = AdaptingFieldProperty(for_interfaces.IBoard['description'])

	ForumCount = property(containers.CheckingLastModifiedBTreeContainer.__len__)

	sharingTargets = ()
	creator = None

@interface.implementer(for_interfaces.IGeneralBoard)
class GeneralBoard(Board):
	__external_can_create__ = False


@interface.implementer(for_interfaces.ICommunityBoard)
class CommunityBoard(GeneralBoard):
	__external_can_create__ = False



@interface.implementer(for_interfaces.ICommunityBoard)
@component.adapter(nti_interfaces.ICommunity)
def GeneralBoardCommunityAdapter(community):
	"""
	For the moment, we will say that all communities have a single board, in the same
	way that all users have a blog. Only administrators can create forums
	within the board (with the exception of a single default, general
	purpose forum that always exists)
	"""
	# TODO: Note the similarity to personalBlogAdapter
	annotations = an_interfaces.IAnnotations( community )
	board = annotations.get( CommunityBoard.__default_name__ )
	if board is None:
		board = CommunityBoard()
		annotations[CommunityBoard.__default_name__] = board
		board.__parent__ = community
		board.creator = community
		board.title = _('Discussion Board')

		jar = IConnection( community, None )
		if jar:
			jar.add( board )
		errors = schema.getValidationErrors( for_interfaces.ICommunityBoard, board )
		if errors:
			__traceback_info__ = errors
			raise errors[0][1]
	return board
