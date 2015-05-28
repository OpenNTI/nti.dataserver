#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Discussion board/forum objects.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver.contenttypes.forums import MessageFactory as _

from zope import schema
from zope import interface
from zope import component

from zope.cachedescriptors.property import cachedIn

# Board

from nti.contentlibrary.interfaces import IContentPackageBundle

from nti.dataserver.interfaces import system_user
from nti.dataserver.contenttypes.forums.board import GeneralBoard
from nti.dataserver.contenttypes.forums.board import AnnotatableBoardAdapter

from nti.externalization.oids import to_external_ntiid_oid

from nti.ntiids.ntiids import TYPE_OID

from .interfaces import IContentBoard

@interface.implementer(IContentBoard)
class ContentBoard(GeneralBoard):
	mime_type = mimeType = 'application/vnd.nextthought.forums.contentboard'

	# Override things related to ntiids.
	# These don't have global names, so they must be referenced
	# by OID. We are also IUseOIDForNTIID so our children
	# inherit this.
	NTIID_TYPE = _ntiid_type = TYPE_OID
	NTIID = cachedIn('_v_ntiid')(to_external_ntiid_oid)

	# Who owns this? Who created it?
	# Right now, we're saying "system" did it...
	# see also the sharing targets
	creator = system_user

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

@interface.implementer(IContentBoard)
def ContentBoardAdapter(context):
	board = AnnotatableBoardAdapter(context, ContentBoard, IContentBoard)
	if board.creator is None or IContentPackageBundle.providedBy(context):
		board.creator = system_user
	return board

# Forum

from nti.dataserver.contenttypes.forums.forum import GeneralForum

from .interfaces import IContentForum

@interface.implementer(IContentForum)
class ContentForum(GeneralForum):
	__external_can_create__ = True
	mime_type = mimeType = 'application/vnd.nextthought.forums.contentforum'

	@property
	def _mask_creator(self):
		return (self.creator != system_user)

	def xxx_isReadableByAnyIdOfUser(self, remote_user, my_ids, family):
		# if we get here, we're authenticated
		# See above about the sharing stuff
		return True

# Topic

from nti.dataserver import users
from nti.dataserver.interfaces import IDefaultPublished
from nti.dataserver.contenttypes.forums.topic import GeneralHeadlineTopic

from .interfaces import IContentHeadlineTopic

@interface.implementer(IContentHeadlineTopic)
class ContentHeadlineTopic(GeneralHeadlineTopic):
	__external_can_create__ = True
	mimeType = 'application/vnd.nextthought.forums.contentheadlinetopic'

	@property
	def sharingTargetsWhenPublished(self):
		# Instead of returning the default set from super, which would return
		# the dynamic memberships of the *creator* of this object, we
		# make it visible to the world
		# XXX NOTE: This will change as I continue to flesh out
		# the permissioning of the content bundles themselves
		# auth = IPrincipal( AUTHENTICATED_GROUP_NAME )
		# interface.alsoProvides(auth, IEntity)
		return (users.Entity.get_entity('Everyone'),)

	@property
	def flattenedSharingTargetNames(self):
		result = super(ContentHeadlineTopic, self).flattenedSharingTargetNames
		if 'Everyone' in result:
			result.add('system.Everyone')
		return result

	def isSharedWith(self, wants):
		res = super(ContentHeadlineTopic, self).isSharedWith(wants)
		if not res:
			# again, implicitly with everyone
			res = IDefaultPublished.providedBy(self)
		return res

# Posts

from nti.dataserver.contenttypes.forums.post import GeneralHeadlinePost
from nti.dataserver.contenttypes.forums.post import GeneralForumComment

from .interfaces import IContentCommentPost
from .interfaces import IContentHeadlinePost

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

# ACLs

from nti.dataserver.contenttypes.forums.acl import _CommunityForumACLProvider
from nti.dataserver.contenttypes.forums.acl import _CommunityBoardACLProvider

from nti.dataserver.authorization_acl import ace_allowing
from nti.dataserver.interfaces import AUTHENTICATED_GROUP_NAME

from nti.dataserver.authorization import ACT_READ

@component.adapter(IContentBoard)
class _ContentBoardACLProvider(_CommunityBoardACLProvider):
	"""
	We want exactly the same thing as the community gets:
	admins can create/delete forums, and the creator gets nothing special,
	with nothing inherited.
	"""

	def _extend_acl_after_creator_and_sharing(self, acl):
		acl.append(ace_allowing(AUTHENTICATED_GROUP_NAME, ACT_READ, ContentBoard))

		# acl.append( ace_allowing( prin, ACT_CREATE, ContentBoard ))
		super(_ContentBoardACLProvider, self)._extend_acl_after_creator_and_sharing(acl)

@component.adapter(IContentForum)
class _ContentForumACLProvider(_CommunityForumACLProvider):
	"""
	Lets everyone create entries inside it right now.
	"""

	def _get_sharing_target_names(self):
		return ('Everyone', AUTHENTICATED_GROUP_NAME)

# Forum decorators

from nti.externalization.singleton import SingletonDecorator
from nti.externalization.interfaces import StandardExternalFields
from nti.externalization.interfaces import IExternalMappingDecorator

from nti.links.links import Link

# These imports are broken out explicitly for speed (avoid runtime attribute lookup)
LINKS = StandardExternalFields.LINKS

@interface.implementer(IExternalMappingDecorator)
class ContentBoardLinkDecorator(object):
	# XXX Very similar to the decorators for Community and PersonalBlog;
	# can we unify these?
	__metaclass__ = SingletonDecorator

	def decorateExternalMapping(self, context, mapping):
		# TODO: This may be slow, if the forum doesn't persistently
		# exist and we keep creating it and throwing it away (due to
		# not commiting on GET)
		board = IContentBoard(context, None)
		if board is not None:  # Not checking security. If the community is visible to you, the forum is too
			the_links = mapping.setdefault(LINKS, [])
			link = Link(board, rel=board.__name__)
			# link_belongs_to_user( link, context )
			the_links.append(link)
