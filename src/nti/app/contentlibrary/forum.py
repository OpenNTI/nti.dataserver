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

	mimeType = 'application/vnd.nextthought.forums.contentboard'

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

	mimeType = 'application/vnd.nextthought.forums.contentforum'

### Topic

from .interfaces import IContentHeadlineTopic
from .interfaces import NTIID_TYPE_CONTENT_TOPIC

from nti.dataserver.contenttypes.forums.topic import GeneralHeadlineTopic

from nti.dataserver.interfaces import IPrincipal
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

@interface.implementer(IContentHeadlineTopic)
class ContentHeadlineTopic(GeneralHeadlineTopic):

	_ntiid_type = NTIID_TYPE_CONTENT_TOPIC

	mimeType = 'application/vnd.nextthought.forums.contentheadlinetopic'

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
	mimeType = 'application/vnd.nextthought.forums.contentheadlinepost'

@interface.implementer(IContentCommentPost)
class ContentCommentPost(GeneralForumComment):
	mimeType = 'application/vnd.nextthought.forums.contentheadlinecomment'


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

### Forum views

from pyramid.view import view_config
from pyramid.view import view_defaults

### XXX: Finish refactoring this to break the dependency
from nti.app.forums.views import _AbstractForumPostView
from nti.app.forums.views import _AbstractTopicPostView
from nti.app.forums.views import _c_view_defaults
from nti.app.forums import VIEW_CONTENTS

@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=IContentForum,
				**_c_view_defaults )
class ContentForumPostView(_AbstractForumPostView):
	""" Given an incoming IPost, creates a new topic in the content forum """

	_constraint = IContentHeadlinePost.providedBy
	@property
	def _override_content_type(self):
		return ContentHeadlinePost.mimeType
	_factory = ContentHeadlineTopic


@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=IContentHeadlineTopic,
				**_c_view_defaults )
class ContentHeadlineTopicPostView(_AbstractTopicPostView):
	"""
	Add a comment to a topic.
	"""
	_constraint = IContentCommentPost.providedBy
	@property
	def _override_content_type(self):
		return ContentCommentPost.mimeType
