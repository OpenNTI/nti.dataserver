#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Related to traversing into forum objects.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.container.traversal import ContainerTraversable
from zope.traversing.interfaces import TraversalError

from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces
from nti.dataserver.contenttypes.forums.forum import CommunityForum
_FORUM_NAME = CommunityForum.__default_name__

from nti.appserver._adapters import GenericModeledContentExternalFieldTraverser

@component.adapter(frm_interfaces.IPost)
class _PostFieldTraverser(GenericModeledContentExternalFieldTraverser):
	"Disallow updates to the sharedWith field of blog posts/comments"
	_allowed_fields = tuple( set(GenericModeledContentExternalFieldTraverser._allowed_fields) - set( ('sharedWith',)) )


@component.adapter(frm_interfaces.ICommunityBoard)
class _CommunityBoardTraversable(ContainerTraversable):
	"""
	Allows traversing to the default forum, creating it on demand.
	"""

	def traverse(self, name, furtherPath):
		if name not in self._container and name == _FORUM_NAME:
			try:
				return frm_interfaces.ICommunityForum( self._container.creator ) # Ask the ICommunity
			except TypeError: # pragma: no cover
				raise TraversalError( self._container, name ) # No adapter

		return super(_CommunityBoardTraversable,self).traverse(name, furtherPath)
