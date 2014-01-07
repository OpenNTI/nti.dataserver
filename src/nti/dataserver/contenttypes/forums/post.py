#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for forum posts.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.schema.fieldproperty import FieldProperty
from zope.annotation import interfaces as an_interfaces

from persistent import Persistent

from nti.dataserver import datastructures
from nti.dataserver import sharing

from nti.utils.schema import AdaptingFieldProperty

from ..note import BodyFieldProperty
from ..threadable import ThreadableMixin

from ._compat import Implicit
from . import _containerIds_from_parent
from . import interfaces as for_interfaces

@interface.implementer(for_interfaces.IPost, an_interfaces.IAttributeAnnotatable)
class Post(
		   Persistent,
		   datastructures.ZContainedMixin,
		   datastructures.CreatedModDateTrackingObject,
		   sharing.AbstractReadableSharedWithMixin,
		   Implicit):

	mimeType = None

	body = BodyFieldProperty(for_interfaces.IPost['body'])

	title = AdaptingFieldProperty(for_interfaces.IPost['title'])
	tags = FieldProperty(for_interfaces.IPost['tags'])

	sharingTargets = ()

	id, containerId = _containerIds_from_parent()

	def __eq__( self, other ):
		try:
			return other == (self.id, self.__parent__, self.title, self.body, self.creator)
		except AttributeError: # pragma: no cover
			# XXX: FIXME: This shouldn't be possible. And yet:
			#  Module nti.appserver.pyramid_authorization:105 in _lineage_that_ensures_acls
			#  >>  acl = cache.get( location )
			#  Module nti.dataserver.contenttypes.forums.post:52 in __eq__
			#  >>  return other == (self.id, self.__parent__, self.title, self.body, self.creator)
			#  AttributeError: 'CommunityHeadlinePost' object has no attribute 'creator'
			logger.exception("Unexpected attribute error comparing a post")
			return NotImplemented

	def __hash__( self ):
		return hash( (self.id, self.containerId, self.title, tuple(self.body or ()), self.creator) )

@interface.implementer(for_interfaces.IHeadlinePost)
class HeadlinePost(Post):
	pass

@interface.implementer(for_interfaces.IGeneralPost)
class GeneralPost(Post):
	pass

@interface.implementer(for_interfaces.ICommentPost)
class CommentPost(Post, ThreadableMixin):
	pass

# These last are never permissioned separately, only
# inherited. The inheritance is expressed through the ACLs, but
# in is convenient for the actual values to be accessible down here too.
# We have to do something special to override the default value set in the
# class we inherit from. cf topic.PersonalBlogEntry
# TODO: Still not sure this is really correct
from . import _AcquiredSharingTargetsProperty

@interface.implementer(for_interfaces.IGeneralHeadlinePost)
class GeneralHeadlinePost(GeneralPost,HeadlinePost):
	sharingTargets = _AcquiredSharingTargetsProperty()

@interface.implementer(for_interfaces.IGeneralForumComment)
class GeneralForumComment(GeneralPost,
						  CommentPost):
	sharingTargets = _AcquiredSharingTargetsProperty()

@interface.implementer(for_interfaces.ICommunityHeadlinePost)
class CommunityHeadlinePost(GeneralHeadlinePost):
	pass

@interface.implementer(for_interfaces.IPersonalBlogEntryPost)
class PersonalBlogEntryPost(HeadlinePost):
	sharingTargets = _AcquiredSharingTargetsProperty()

@interface.implementer(for_interfaces.IPersonalBlogComment)
class PersonalBlogComment(CommentPost):
	sharingTargets = _AcquiredSharingTargetsProperty()

#	@CachedProperty
#	def NTIID(self):
#		return ntiids.make_ntiid( date=ntiids.DATE,
#								  provider=self._creator_username,
#								  nttype=ntiids.TYPE_MEETINGROOM_GROUP,
#								  specific=ntiids.escape_provider(self.username.lower()))
