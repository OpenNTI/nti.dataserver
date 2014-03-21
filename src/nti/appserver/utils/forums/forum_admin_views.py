#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Views relating to forum administration.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import MessageFactory as _

logger = __import__('logging').getLogger(__name__)

import collections

from zope import interface

import pyramid.httpexceptions as hexc

from pyramid.view import view_config

from nti.dataserver import users
from nti.dataserver import authorization as nauth
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.externalization.internalization import find_factory_for
from nti.externalization.internalization import update_from_external_object

from nti.appserver.utils import _JsonBodyView

def _parse_external_forum_acl(acl):
	ace_lst = []
	for ace in acl:
		entry = None
		factory = find_factory_for(ace)
		if factory:
			entry = factory()
			update_from_external_object(entry, ace, notify=False)
			if frm_interfaces.IForumACE.providedBy(entry):
				ace_lst.append(entry)
	if not ace_lst:
		raise hexc.HTTPUnprocessableEntity(detail=_('Invalid ACL specification'))
	return ace_lst

def _validate_and_parse_external_forum_acl(acl):
	if not acl:
		return hexc.HTTPNoContent()
	elif not isinstance(acl, collections.Sequence):
		raise hexc.HTTPUnprocessableEntity(detail='Invalid ACL specification')
	else:
		acl = _parse_external_forum_acl(acl)
	return acl

@view_config(route_name='objects.generic.traversal',
			 name='set_community_board_acl',
			 request_method='POST',
			 permission=nauth.ACT_MODERATE)
class SetCommunityBoardACL(_JsonBodyView):

	def __call__(self):
		values = self.readInput()
		community = values.get('community', '')
		community = users.Community.get_community(community)
		if not community or not nti_interfaces.ICommunity.providedBy(community):
			raise hexc.HTTPNotFound(detail=_('Community not found'))

		acl = values.get('acl', ())
		acl = _validate_and_parse_external_forum_acl(acl)

		board = frm_interfaces.ICommunityBoard(community, None)
		if board is None:
			raise hexc.HTTPNotFound(detail=_('Board not found'))

		if not frm_interfaces.IACLCommunityBoard.providedBy(board):
			interface.alsoProvides(board, frm_interfaces.IACLCommunityBoard)

		# set acl
		setattr(board, 'ACL', acl)
		board.updateLastMod()
		return hexc.HTTPNoContent()

def _validate_community(values):
	community = values.get('community', '')
	community = users.Community.get_community(community)
	if not community or not nti_interfaces.ICommunity.providedBy(community):
		raise hexc.HTTPNotFound(detail=_('Community not found'))
	return community

def _validate_community_forum(community, values):
	board = frm_interfaces.ICommunityBoard(community, None)
	if board is None:
		raise hexc.HTTPNotFound(detail=_('Board not found'))

	forum = values.get('forum', None)
	if not forum:  # default forum
		forum = frm_interfaces.ICommunityForum(community, None)
		if forum is None:
			raise hexc.HTTPUnprocessableEntity(detail=_('Community does not allow a forum'))
	else:
		forum = board.get(forum, None)
		if forum is None:
			raise hexc.HTTPNotFound(detail=_('Forum not found'))
	return forum

@view_config(route_name='objects.generic.traversal',
			 name='set_community_forum_acl',
			 request_method='POST',
			 permission=nauth.ACT_MODERATE)
class SetCommunityForumACL(_JsonBodyView):

	def __call__(self):
		values = self.readInput()
		community = _validate_community(values)

		board = frm_interfaces.ICommunityBoard(community, None)
		if board is None:
			raise hexc.HTTPNotFound(detail=_('Board not found'))

		forum = _validate_community_forum(community, values)

		acl = values.get('acl', ())
		acl = _validate_and_parse_external_forum_acl(acl)

		if not frm_interfaces.IACLCommunityForum.providedBy(forum):
			interface.alsoProvides(forum, frm_interfaces.IACLCommunityForum)

		setattr(forum, 'ACL', acl)
		forum.updateLastMod()
		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name='delete_community_forum',
			 request_method='POST',
			 permission=nauth.ACT_MODERATE)
class DeleteCommunityForum(_JsonBodyView):

	def __call__(self):
		values = self.readInput()
		community = values.get('community', '')
		community = users.Community.get_community(community)
		if not community or not nti_interfaces.ICommunity.providedBy(community):
			raise hexc.HTTPNotFound(detail=_('Community not found'))

		forum_name = values.get('forum', None)
		if not forum_name:  # default forum
			raise hexc.HTTPUnprocessableEntity(detail=_('Cannot delete default forum'))
		else:
			board = frm_interfaces.ICommunityBoard(community)
			forum = board.get(forum_name, None)
			if forum is None:
				raise hexc.HTTPNotFound(detail=_('Forum not found'))
			del board[forum_name]
			board.updateLastMod()

		return hexc.HTTPNoContent()

@view_config(route_name='objects.generic.traversal',
			 name='recreate_community_forum',
			 request_method='POST',
			 permission=nauth.ACT_MODERATE)
class RecreateCommunityForum(_JsonBodyView):

	def __call__(self):
		values = self.readInput()
		community = values.get('community', '')
		forum_name = values.get('forum', '')
		community = users.Community.get_community(community)
		if not community or not nti_interfaces.ICommunity.providedBy(community):
			raise hexc.HTTPNotFound(detail=_('Community not found'))

		if not forum_name:
			forum_name = CommunityForum.__default_name__

		board = frm_interfaces.ICommunityBoard(community, {})
		forum = board.get(forum_name)
		if forum is None:
			raise hexc.HTTPUnprocessableEntity(detail=_('Forum not found'))

		# get copy of the data
		data = dict(forum)

		# remove old forum
		del board[forum_name]

		# recrete
		new_forum = CommunityForum()
		new_forum.creator = community
		board[forum_name] = new_forum
		new_forum.title = forum.title

		# reassign
		for k, v in data.items():
			new_forum[k] = v
			v.__parent__ = new_forum  # reset
		board.updateLastMod()

		# clean
		forum.__name__ = forum.__parent__ = None

		return hexc.HTTPNoContent()
