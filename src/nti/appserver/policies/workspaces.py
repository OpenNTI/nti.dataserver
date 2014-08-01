#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration of workspaces for forum objects, in particular, user blogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.appserver.interfaces import IContainerCollection
from nti.appserver.interfaces import IUserWorkspace

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard
from nti.dataserver.users.entity import Entity

@interface.implementer(IContainerCollection)
@component.adapter(IUserWorkspace)
class _UserBoardCollection(object):
	"""
	Turns a User into a ICollection of data for their boards.
	"""

	name = 'Boards'
	__name__ = name
	__parent__ = None

	accepts = ()

	def __init__( self, user_workspace ):
		self.__parent__ = user_workspace

	@property
	def container(self):
		site = component.queryUtility( ICommunitySitePolicyUserEventListener )
		community_name = getattr( site, 'COM_USERNAME', None )
		community = Entity.get_entity( community_name )
		result = []
		if community is not None:
			# We just want the user's community board.
			board = ICommunityBoard( community )
			result.append( board )
		return result

@interface.implementer(IContainerCollection)
@component.adapter(IUserWorkspace)
def _UserBoardCollectionFactory(workspace):
	return _UserBoardCollection( workspace )
