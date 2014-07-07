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
from zope import component
from zope import schema

from nti.externalization.oids import to_external_ntiid_oid

### Board

from .interfaces import IContentBoard
from .interfaces import NTIID_TYPE_CONTENT_BOARD

#from nti.dataserver.contenttypes.forums import _CreatedNamedNTIIDMixin
from nti.dataserver.contenttypes.forums.board import GeneralBoard
from nti.dataserver.contenttypes.forums.board import AnnotatableBoardAdapter

@interface.implementer(IContentBoard)
class ContentBoard(GeneralBoard):
	_ntiid_type = NTIID_TYPE_CONTENT_BOARD

	mime_type = mimeType = 'application/vnd.nextthought.forums.contentboard'


	@property
	def NTIID(self):
		# Fall-back to OIDs for now
		return to_external_ntiid_oid(self)

	def createDefaultForum(self):
		if ContentForum.__default_name__ in self:
			return self[ContentForum.__default_name__]

		forum = ContentForum()
		forum.creator = self.creator
		self[forum.__default_name__] = forum
		forum.title = _('Forum')

		errors = schema.getValidationErrors(IContentForum, forum)
		if errors:
			__traceback_info__ = errors
			raise errors[0][1]
		return forum

	def __setitem__(self, k, v):
		return GeneralBoard.__setitem__(self, k, v)


from nti.dataserver.interfaces import system_user

@interface.implementer(IContentBoard)
def ContentBoardAdapter(context):
	board = AnnotatableBoardAdapter(context, ContentBoard, IContentBoard)
	# Who owns this? Who created it?
	# Right now, we're saying "system" did it...
	# see also the sharing targets
	board.creator = system_user
	return board

### Forum

from .interfaces import IContentForum
from .interfaces import NTIID_TYPE_CONTENT_FORUM

from nti.dataserver.contenttypes.forums.forum import GeneralForum

@interface.implementer(IContentForum)
class ContentForum(GeneralForum):
	_ntiid_type = NTIID_TYPE_CONTENT_FORUM

	mime_type = mimeType = 'application/vnd.nextthought.forums.contentforum'

	@property
	def NTIID(self):
		# Fall-back to OIDs for now
		return to_external_ntiid_oid(self)

	def xxx_isReadableByAnyIdOfUser(self, remote_user, my_ids, family):
		# if we get here, we're authenticated
		# See above about the sharing stuff
		return True

### Topic

from .interfaces import IContentHeadlineTopic
from .interfaces import NTIID_TYPE_CONTENT_TOPIC

from nti.dataserver.contenttypes.forums.topic import GeneralHeadlineTopic
from nti.dataserver import users
from nti.dataserver.interfaces import IDefaultPublished

@interface.implementer(IContentHeadlineTopic)
class ContentHeadlineTopic(GeneralHeadlineTopic):

	_ntiid_type = NTIID_TYPE_CONTENT_TOPIC

	mimeType = 'application/vnd.nextthought.forums.contentheadlinetopic'

	@property
	def NTIID(self):
		# Fall-back to OIDs for now
		return to_external_ntiid_oid(self)


	@property
	def sharingTargetsWhenPublished(self):
		# Instead of returning the default set from super, which would return
		# the dynamic memberships of the *creator* of this object, we
		# make it visible to the world
		# XXX NOTE: This will change as I continue to flesh out
		# the permissioning of the content bundles themselves
		#auth = IPrincipal( AUTHENTICATED_GROUP_NAME )
		#interface.alsoProvides(auth, IEntity)
		return (users.Entity.get_entity('Everyone'),)

	@property
	def flattenedSharingTargetNames(self):
		result = super(ContentHeadlineTopic, self).flattenedSharingTargetNames
		if 'Everyone' in result:
			result.add('system.Everyone')
		return result

	def isSharedWith(self, wants):
		res = super(ContentHeadlineTopic,self).isSharedWith(wants)
		if not res:
			# again, implicitly with everyone
			res = IDefaultPublished.providedBy(self)
		return res

### Posts

from .interfaces import IContentHeadlinePost
from .interfaces import IContentCommentPost

from nti.dataserver.contenttypes.forums.post import GeneralHeadlinePost
from nti.dataserver.contenttypes.forums.post import GeneralForumComment

@interface.implementer(IContentHeadlinePost)
class ContentHeadlinePost(GeneralHeadlinePost):
	mime_type = mimeType = 'application/vnd.nextthought.forums.contentheadlinepost'

@interface.implementer(IContentCommentPost)
class ContentCommentPost(GeneralForumComment):
	mime_type = mimeType = 'application/vnd.nextthought.forums.contentforumcomment'

	def xxx_isReadableByAnyIdOfUser(self, remote_user, my_ids, family):
		# if we get here, we're authenticated
		# See above about the sharing stuff
		return True

### ACLs

from nti.dataserver.contenttypes.forums.acl import _CommunityForumACLProvider
from nti.dataserver.contenttypes.forums.acl import _CommunityBoardACLProvider

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

from nti.dataserver.authorization import ACT_READ
from nti.dataserver.authorization import ACT_CREATE

@component.adapter(IContentBoard)
class _ContentBoardACLProvider(_CommunityBoardACLProvider):
	"""
	We want exactly the same thing as the community gets:
	admins can create/delete forums, and the creator gets nothing special,
	with nothing inherited.
	"""

	def _extend_acl_after_creator_and_sharing(self, acl):
		acl.append( ace_allowing( AUTHENTICATED_GROUP_NAME, ACT_READ, ContentBoard ))

		#acl.append( ace_allowing( prin, ACT_CREATE, ContentBoard ))
		super(_ContentBoardACLProvider,self)._extend_acl_after_creator_and_sharing(acl)

@component.adapter(IContentForum)
class _ContentForumACLProvider(_CommunityForumACLProvider):
	"""
	Lets everyone create entries inside it right now.
	"""

	def _get_sharing_target_names(self):
		return ('Everyone', AUTHENTICATED_GROUP_NAME)

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
from nti.app.forums.views import AbstractBoardPostView
from nti.app.forums.views import _c_view_defaults
from nti.app.forums import VIEW_CONTENTS


@view_config( name='' )
@view_config( name=VIEW_CONTENTS )
@view_defaults( context=IContentBoard,
				**_c_view_defaults)
class ContentBoardPostView(AbstractBoardPostView):
	_forum_factory = ContentForum

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
