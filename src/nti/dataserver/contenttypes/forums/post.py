#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for forum posts.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.lifecycleevent import IObjectModifiedEvent

from zope.schema.fieldproperty import FieldProperty

from Acquisition import Implicit

from nti.coremetadata.mixins import MentionableMixin
from nti.coremetadata.mixins import ZContainedMixin

from nti.dataserver.contenttypes.forums import _containerIds_from_parent

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import ICommentPost
from nti.dataserver.contenttypes.forums.interfaces import IGeneralPost
from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IDFLHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForumComment
from nti.dataserver.contenttypes.forums.interfaces import IGeneralHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogComment
from nti.dataserver.contenttypes.forums.interfaces import ICommunityHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost

from nti.dataserver.contenttypes.note import BodyFieldProperty

from nti.dataserver.sharing import AbstractReadableSharedWithMixin

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.schema.fieldproperty import AdaptingFieldProperty

from nti.threadable.threadable import Threadable as ThreadableMixin


@interface.implementer(IPost, IAttributeAnnotatable)
class Post(ZContainedMixin,
           MentionableMixin,
           PersistentCreatedModDateTrackingObject,
           AbstractReadableSharedWithMixin,
           Implicit):

    mimeType = None

    body = BodyFieldProperty(IPost['body'])

    title = AdaptingFieldProperty(IPost['title'])
    tags = FieldProperty(IPost['tags'])

    sharingTargets = ()

    id, containerId = _containerIds_from_parent()

    def __eq__(self, other):
        try:
            return other == (self.id, self.__parent__, self.title, self.body, self.creator)
        except AttributeError:  # pragma: no cover
            # XXX: FIXME: This shouldn't be possible. And yet:
            #  Module nti.appserver.pyramid_authorization:105 in _lineage_that_ensures_acls
            #  >>  acl = cache.get( location )
            #  Module nti.dataserver.contenttypes.forums.post:52 in __eq__
            #  >>  return other == (self.id, self.__parent__, self.title, self.body, self.creator)
            # AttributeError: 'CommunityHeadlinePost' object has no attribute
            # 'creator'
            logger.exception("Unexpected attribute error comparing a post")
            return NotImplemented

    def __hash__(self):
        return hash((self.id, self.containerId, self.title, 
                     tuple(self.body or ()), self.creator))


@interface.implementer(IHeadlinePost)
class HeadlinePost(Post):
    pass


@component.adapter(IHeadlinePost, IObjectModifiedEvent)
def _update_forum_when_headline_modified(modified_object, _):
    """
    When a headline post, contained inside a topic contained inside a forum
    is modified, the modification needs to percolate all the way up to the forum
    so that we know its \"contents\" listing is out of date.
    Generic listeners handle everything except the grandparent level (the forum).
    """
    try:
        parent =  modified_object.__parent__.__parent__
        parent.updateLastModIfGreater(modified_object.lastModified)
    except AttributeError:
        pass


@interface.implementer(IGeneralPost)
class GeneralPost(Post):
    pass


@interface.implementer(ICommentPost)
class CommentPost(Post, ThreadableMixin):
    pass


# These last are never permissioned separately, only
# inherited. The inheritance is expressed through the ACLs, but
# in is convenient for the actual values to be accessible down here too.
# We have to do something special to override the default value set in the
# class we inherit from. cf topic.PersonalBlogEntry
# TODO: Still not sure this is really correct
from nti.dataserver.contenttypes.forums import _AcquiredSharingTargetsProperty


@interface.implementer(IGeneralHeadlinePost)
class GeneralHeadlinePost(GeneralPost, HeadlinePost):
    sharingTargets = _AcquiredSharingTargetsProperty()


@interface.implementer(IGeneralForumComment)
class GeneralForumComment(GeneralPost, CommentPost):
    sharingTargets = _AcquiredSharingTargetsProperty()


@interface.implementer(ICommunityHeadlinePost)
class CommunityHeadlinePost(GeneralHeadlinePost):
    pass


@interface.implementer(IDFLHeadlinePost)
class DFLHeadlinePost(GeneralHeadlinePost):
    pass


@interface.implementer(IPersonalBlogEntryPost)
class PersonalBlogEntryPost(HeadlinePost):
    sharingTargets = _AcquiredSharingTargetsProperty()


@interface.implementer(IPersonalBlogComment)
class PersonalBlogComment(CommentPost):
    sharingTargets = _AcquiredSharingTargetsProperty()
