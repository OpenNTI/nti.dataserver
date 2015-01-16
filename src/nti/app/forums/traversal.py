#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Related to traversing into forum objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope.traversing.interfaces import TraversalError
from zope.container.traversal import ContainerTraversable

from nti.appserver._adapters import GenericModeledContentExternalFieldTraverser

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IDefaultForumBoard

from nti.dataserver.contenttypes.forums.forum import CommunityForum

_FORUM_NAME = CommunityForum.__default_name__

@component.adapter(IPost)
class _PostFieldTraverser(GenericModeledContentExternalFieldTraverser):
	"""
	Disallow updates to the sharedWith field of blog posts/comments
	"""
	_allowed_fields = tuple( set(GenericModeledContentExternalFieldTraverser._allowed_fields) - set( ('sharedWith',)) )

@component.adapter(IDefaultForumBoard)
class _DefaultForumBoardTraversable(ContainerTraversable):
	"""
	Allows traversing to the default forum, creating it on demand.
	"""

	def traverse(self, name, furtherPath):
		if name not in self._container and name == _FORUM_NAME:
			try:
				return self._container.createDefaultForum()
			except (TypeError,AttributeError): # pragma: no cover
				raise TraversalError( self._container, name ) # No adapter

		result = ContainerTraversable.traverse(self, name, furtherPath)
		return result
