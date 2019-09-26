#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for forums.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import datetime

from zope import schema
from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.intid.interfaces import IIntIds
from zope.intid.interfaces import IIntIdAddedEvent

from ZODB.interfaces import IConnection

from Acquisition import Implicit

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IRedisClient
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.containers.containers import AcquireObjectsOnReadMixin
from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.coremetadata.mixins import ZContainedMixin

from nti.dataserver.contenttypes.forums import MessageFactory as _

from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_DFL_FORUM
from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_GENERAL_FORUM
from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_PERSONAL_BLOG
from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_COMMUNITY_FORUM

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IBoard
from nti.dataserver.contenttypes.forums.interfaces import IForum
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IDFLBoard
from nti.dataserver.contenttypes.forums.interfaces import IDFLForum
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForum
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard
from nti.dataserver.contenttypes.forums.interfaces import ICommunityForum
from nti.dataserver.contenttypes.forums.interfaces import IACLCommunityForum

from nti.dataserver.contenttypes.forums import _containerIds_from_parent
from nti.dataserver.contenttypes.forums import _CreatedIntIdNTIIDMixin as _SingleInstanceIntIdMixin
from nti.dataserver.contenttypes.forums import _CreatedNamedNTIIDMixin as _SingleInstanceNTIIDMixin

from nti.dataserver.sharing import AbstractReadableSharedWithMixin

from nti.schema.fieldproperty import AdaptingFieldProperty

from nti.transactions import transactions

from nti.traversal.traversal import find_interface

_NEWEST_TTL = datetime.timedelta(days=7)

#: The __name__ of the default forum
DEFAULT_FORUM_KEY = u'Forum'

#: The default title of the default forum
DEFAULT_FORUM_NAME = u'General Discussion'
DEFAULT_PERSONAL_BLOG_NAME = u'Blog'


def query_uid(obj, intids=None):
    intids = component.getUtility(IIntIds) if intids is None else intids
    result = intids.queryId(obj)
    return result


def query_object(uid, intids=None):
    intids = component.getUtility(IIntIds) if intids is None else intids
    try:
        # JAM: FIXME: Shouldn't this be long? We need to check the family
        result = intids.queryObject(int(uid), None)
        if hasattr(result, '_p_activate'):
            result._p_activate()
    except (TypeError, ValueError):
        result = None
    except KeyError:  # POSKeyError
        logger.exception("Failed to activate object stored at %s", uid)
        result = None
    return result


@interface.implementer(IForum, IAttributeAnnotatable)
class Forum(Implicit,
            AcquireObjectsOnReadMixin,
            CheckingLastModifiedBTreeContainer,
            ZContainedMixin,
            AbstractReadableSharedWithMixin):

    __external_can_create__ = False

    creator = None
    sharingTargets = ()
    title = AdaptingFieldProperty(IForum['title'])
    description = AdaptingFieldProperty(IBoard['description'])
    TopicCount = property(CheckingLastModifiedBTreeContainer.__len__)

    id, containerId = _containerIds_from_parent()

    _v_newest_descendant = None

    @property
    def NewestDescendantCreatedTime(self):
        item = self.NewestDescendant
        if item is not None:
            return item.createdTime
        return 0.0

    # Unlike with ITopic, we don't want to store this object on the forum
    # itself: that's potentially a tremendous amount of churn (churn
    # from all the topics in the whole forum) (even the churn on a single
    # topic might be too much). Instead, we serialize it out to
    # redis and only store it there. (If we are very careful with __setattr__, we
    # could probably do this with a property.)
    def _descendent_key(self):
        try:
            return 'forums/' + self.containerId + '/' + self.id + '/newestDescendant'
        except TypeError:
            # This should only happen in tests
            logger.warn("No stable key for newestDescendant of %s", self)
            return 'broken/' + unicode(id(self)) + '/newestDescendant'

    def _get_NewestDescendant(self):
        # 1. Local cache (this may get slightly stale, but not
        # too stale) (Confirm that)
        newest_object = self._v_newest_descendant

        # 2. Remote cache
        if newest_object is None:
            redis = component.getUtility(IRedisClient)
            data = redis.get(self._descendent_key())
            newest_object = query_object(data) if data else None

        # 3. Lazily finding one
        if newest_object is None and self.TopicCount:
            newest_created = -1.0
            for topic in self.values():
                if topic.createdTime > newest_created:
                    newest_object = topic
                    newest_created = topic.createdTime
                if topic.NewestDescendantCreatedTime > newest_created:
                    newest_object = topic.NewestDescendant
                    newest_created = topic.NewestDescendantCreatedTime

        # If we found one, it may have been cached locally
        # or externally. If it was local, we need to be sure
        # its still in the catalog
        if newest_object is not None and query_uid(newest_object):
            # Notice that we cache this locally on the object for
            # this thread, but we DO NOT cache it externally.
            # This is because this is probably a GET request
            # and wouldn't be safe to store it anyway. Also,
            # there's bound to be write activity that updates it soon
            # anyway, so the only time we have to resort to method 3
            # should be extremely rare
            self._v_newest_descendant = newest_object
            return newest_object

    def _set_NewestDescendant(self, descendant):
        uid = query_uid(descendant)
        if uid:
            self._v_newest_descendant = descendant

            redis = component.getUtility(IRedisClient)
            args = (redis, unicode(uid),)
            transactions.do_near_end(target=self,
                                     call=self._publish_descendant_to_redis,
                                     args=args)

    def _publish_descendant_to_redis(self, redis, data):
        redis.setex(self._descendent_key(), _NEWEST_TTL, data)

    NewestDescendant = property(_get_NewestDescendant)


@component.adapter(IPost, IIntIdAddedEvent)
def _post_added_to_topic(post, _):
    """
    Watch for a post to be added to a topic and keep track of the
    creation time of the latest post within the entire forum.

    The ContainerModifiedEvent does not give us the object (post)
    and it also can't tell us if the post was added or removed.
    """
    forum = find_interface(post, IForum, strict=False)
    if forum is not None:
        forum._set_NewestDescendant(post)


@component.adapter(ITopic, IIntIdAddedEvent)
def _topic_added_to_forum(topic, _):
    """
    Watch for a topic to be added to a forum and keep track of the
    creation time of the latest topic within the entire forum.

    The ContainerModifiedEvent does not give us the object (post)
    and it also can't tell us if the post was added or removed.
    """
    # Note that we don't have a IIntIdRemoved listener
    # for this. It's extremely unlikely that a topic will be
    # removed while it is still the newest in the forum, and
    # if that is the case, it's no big loss
    if IForum.providedBy(topic.__parent__):
        topic.__parent__._set_NewestDescendant(topic)


@interface.implementer(IPersonalBlog)
class PersonalBlog(Forum, _SingleInstanceNTIIDMixin):

    __external_can_create__ = False

    __name__ = __blog_name__ = __default_name__ = DEFAULT_PERSONAL_BLOG_NAME
    _ntiid_type = NTIID_TYPE_PERSONAL_BLOG


@interface.implementer(IPersonalBlog)
@component.adapter(IUser)
def PersonalBlogAdapter(user):
    """
    Adapts a user to his one-and-only :class:`IPersonalBlog` entry.
    This object is stored as a container under the user, named both
    :const:`PersonalBlog.__name__` and for its NTIID.
    """

    # The right key is critical. 'Blog' is the pretty external name
    # (see dataserver_pyramid_traversal)

    # some types of users (test users usually) have no containers
    containers = getattr(user, 'containers', None)
    if containers is None:
        return None

    # For convenience, we register the container with
    # both its NTIID and its short name
    forum = containers.getContainer(PersonalBlog.__blog_name__)
    if forum is None:
        forum = PersonalBlog()
        forum.__parent__ = user
        forum.creator = user
        # in the past we set it explicitly
        assert forum.__name__ == PersonalBlog.__blog_name__
        forum.title = user.username

        # TODO: Events?
        containers.addContainer(forum.__name__, forum, locate=False)
        containers.addContainer(forum.NTIID, forum, locate=False)

        jar = IConnection(user, None)
        if jar:
            jar.add(forum)  # ensure we store with the user
        errors = schema.getValidationErrors(IPersonalBlog, forum)
        if errors:
            __traceback_info__ = errors
            raise errors[0][1]
    return forum


@interface.implementer(IPersonalBlog)
def NoBlogAdapter(_):
    """
    An adapter that does not actually create an :class:`IPersonalBlog`.

    This is useful as an override when no personal blog is desired but one
    would otherwise be inherited."""
    return None


@interface.implementer(IGeneralForum)
class GeneralForum(Forum, _SingleInstanceNTIIDMixin):
    __external_can_create__ = False
    creator = None
    __name__ = __default_name__ = DEFAULT_FORUM_KEY
    _ntiid_type = NTIID_TYPE_GENERAL_FORUM


@interface.implementer(ICommunityForum)
class CommunityForum(GeneralForum):
    __external_can_create__ = True
    _ntiid_type = NTIID_TYPE_COMMUNITY_FORUM


@interface.implementer(IDFLForum)
class DFLForum(_SingleInstanceIntIdMixin, GeneralForum):
    __external_can_create__ = True
    _ntiid_type = NTIID_TYPE_DFL_FORUM


@component.adapter(ICommunity)
@interface.implementer(ICommunityForum)
def GeneralForumCommunityAdapter(community):
    """
    All communities that have a board (which by default is all communities)
    have at least one default forum in that board. If the board exists,
    but no forum exists, one is added.
    """
    board = ICommunityBoard(community, None)
    if board is None:
        return None  # No board is allowed

    if board:  # contains some forums, yay!
        if len(board) == 1:
            # Whatever the single forum is
            return board.values()[0]
        forum = board.get(CommunityForum.__default_name__)
        if forum is not None:
            return forum

    # Board is empty, or at least doesn't have our desired forum,
    # so create and store it
    forum = CommunityForum()
    forum.creator = community
    board[forum.__default_name__] = forum
    forum.title = _(DEFAULT_FORUM_NAME)

    errors = schema.getValidationErrors(ICommunityForum, forum)
    if errors:
        __traceback_info__ = errors
        raise errors[0][1]
    return forum


@interface.implementer(IACLCommunityForum)
class ACLCommunityForum(CommunityForum):
    __external_can_create__ = False
    mime_type = 'application/vnd.nextthought.forums.communityforum'
    ACL = ()


@interface.implementer(IDFLForum)
@component.adapter(IDynamicSharingTargetFriendsList)
def GeneralForumDFLAdapter(dfl):
    """
    All dfls that have a board (which by default is all dfls)
    have at least one default forum in that board. If the board exists,
    but no forum exists, one is added.
    """
    board = IDFLBoard(dfl, None)
    if board is None:
        return None  # No board is allowed

    if board:  # contains some forums, yay!
        if len(board) == 1:
            # Whatever the single forum is
            return board.values()[0]

        forum = board.get(DFLForum.__default_name__)
        if forum is not None:
            return forum

    # Board is empty, or at least doesn't have our desired forum,
    # so create and store it
    forum = DFLForum()
    forum.creator = dfl
    board[forum.__default_name__] = forum
    forum.title = _(DEFAULT_FORUM_NAME)

    errors = schema.getValidationErrors(IDFLForum, forum)
    if errors:
        __traceback_info__ = errors
        raise errors[0][1]
    return forum
