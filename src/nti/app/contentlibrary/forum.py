#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Discussion board/forum objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: too many ancestors
# pylint: disable=I0011,R0901

from nti.dataserver.contenttypes.forums import MessageFactory as _

from zope import interface
from zope import schema

### Board

from .interfaces import IContentBoard
from .interfaces import NTIID_TYPE_CONTENT_BOARD

from nti.dataserver.contenttypes.forums import _CreatedNamedNTIIDMixin
from nti.dataserver.contenttypes.forums.board import GeneralBoard
from nti.dataserver.contenttypes.forums.board import AnnotatableBoardAdapter

@interface.implementer(IContentBoard)
class ContentBoard(GeneralBoard, _CreatedNamedNTIIDMixin):
	_ntiid_type = NTIID_TYPE_CONTENT_BOARD

	def createDefaultForum(self):
		if ContentForum.__default_name__ in self:
			return self[ContentForum.__default_name__]

		forum = ContentForum()
		#forum.creator = ???
		self[forum.__default_name__] = forum
		forum.title = _('Forum')

		errors = schema.getValidationErrors(IContentForum, forum)
		if errors:
			__traceback_info__ = errors
			raise errors[0][1]
		return forum




@interface.implementer(IContentBoard)
def ContentBoardAdapter(context):
	return AnnotatableBoardAdapter(context, ContentBoard, IContentBoard)

### Forum

from .interfaces import IContentForum
from .interfaces import NTIID_TYPE_CONTENT_FORUM

from nti.dataserver.contenttypes.forums.forum import GeneralForum

@interface.implementer(IContentForum)
class ContentForum(GeneralForum):
	_ntiid_type = NTIID_TYPE_CONTENT_FORUM

### Topic

from .interfaces import IContentHeadlineTopic
from .interfaces import NTIID_TYPE_CONTENT_TOPIC

from nti.dataserver.contenttypes.forums.topic import GeneralHeadlineTopic

from nti.dataserver.interfaces import IPrincipal
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

@interface.implementer(IContentHeadlineTopic)
class ContentHeadlineTopic(GeneralHeadlineTopic):

	_ntiid_type = NTIID_TYPE_CONTENT_TOPIC

	@property
	def sharingTargetsWhenPublished(self):
		# Instead of returning the default set from super, which would return
		# the dynamic memberships of the *creator* of this object, we
		# make it visible to the world
		# XXX NOTE: This will change as I continue to flesh out
		# the permissioning of the content bundles themselves
		return IPrincipal( AUTHENTICATED_GROUP_NAME )

### Posts

from .interfaces import IContentHeadlinePost
from .interfaces import IContentCommentPost

from nti.dataserver.contenttypes.forums.post import GeneralHeadlinePost
from nti.dataserver.contenttypes.forums.post import GeneralForumComment

@interface.implementer(IContentHeadlinePost)
class ContentHeadlinePost(GeneralHeadlinePost):
	pass

@interface.implementer(IContentCommentPost)
class ContentCommentPost(GeneralForumComment):
	pass


### Forum decorators
from nti.externalization.singleton import SingletonDecorator
from nti.externalization import interfaces as ext_interfaces

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
LINKS = ext_interfaces.StandardExternalFields.LINKS

from nti.dataserver.links import Link

@interface.implementer(ext_interfaces.IExternalMappingDecorator)
class ContentBoardLinkDecorator(object):
	#### XXX Very similar to the decorators for Community and PersonalBlog;
	# can we unify these?
	__metaclass__ = SingletonDecorator

	def decorateExternalMapping( self, context, mapping ):
		# TODO: This may be slow, if the forum doesn't persistently
		# exist and we keep creating it and throwing it away (due to
		# not commiting on GET)
		board = IContentBoard( context, None )
		if board is not None: # Not checking security. If the community is visible to you, the forum is too
			the_links = mapping.setdefault( LINKS, [] )
			link = Link( board,
						 rel=board.__name__ )

			#link_belongs_to_user( link, context )
			the_links.append( link )
