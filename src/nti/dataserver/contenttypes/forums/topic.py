#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Definitions for topics.

.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import readproperty
from zope.cachedescriptors.property import CachedProperty

from zope.container.interfaces import INameChooser
from zope.container.contained import ContainerSublocations
from zope.container.contained import dispatchToSublocations

from zope.event import notify

from zope.intid.interfaces import IIntIds
from zope.intid.interfaces import IIntIdAddedEvent

from zope.location.interfaces import ILocationInfo

from zope.schema.fieldproperty import FieldProperty

from zope.security.interfaces import IPrincipal

from Acquisition import Implicit

from nti.containers.containers import AcquireObjectsOnReadMixin
from nti.containers.containers import AbstractNTIIDSafeNameChooser
from nti.containers.containers import CheckingLastModifiedBTreeContainer

from nti.coremetadata.mixins import ZContainedMixin

from nti.dataserver.contenttypes.forums.interfaces import IPost
from nti.dataserver.contenttypes.forums.interfaces import IBoard
from nti.dataserver.contenttypes.forums.interfaces import ITopic
from nti.dataserver.contenttypes.forums.interfaces import IACLEnabled
from nti.dataserver.contenttypes.forums.interfaces import IGeneralForum
from nti.dataserver.contenttypes.forums.interfaces import IGeneralTopic
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog
from nti.dataserver.contenttypes.forums.interfaces import IHeadlineTopic
from nti.dataserver.contenttypes.forums.interfaces import IDFLHeadlineTopic
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntry
from nti.dataserver.contenttypes.forums.interfaces import IGeneralHeadlineTopic
from nti.dataserver.contenttypes.forums.interfaces import ICommunityHeadlineTopic

from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_DFL_TOPIC
from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_GENERAL_TOPIC
from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_COMMUNITY_TOPIC
from nti.dataserver.contenttypes.forums.interfaces import NTIID_TYPE_PERSONAL_BLOG_ENTRY

from nti.dataserver.contenttypes.forums import _CreatedNamedNTIIDMixin
from nti.dataserver.contenttypes.forums import _containerIds_from_parent

from nti.dataserver.interfaces import ACE_ACT_ALLOW

from nti.dataserver.interfaces import IACE
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IACLProvider
from nti.dataserver.interfaces import IWritableShared
from nti.dataserver.interfaces import ObjectSharingModifiedEvent
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.sharing import ShareableMixin
from nti.dataserver.sharing import AbstractReadableSharedWithMixin
from nti.dataserver.sharing import AbstractDefaultPublishableSharedWithMixin

from nti.dataserver.users import Entity

from nti.publishing.interfaces import IDefaultPublished

from nti.schema.fieldproperty import AdaptingFieldProperty
from nti.schema.fieldproperty import AcquisitionFieldProperty

from nti.traversal.traversal import find_interface

from nti.wref.interfaces import IWeakRef


class _AbstractUnsharedTopic(AcquireObjectsOnReadMixin,
                             CheckingLastModifiedBTreeContainer,
                             ZContainedMixin,
                             Implicit):

    creator = None

    tags = FieldProperty(IPost['tags'])
    title = AdaptingFieldProperty(ITopic['title'])
    description = AdaptingFieldProperty(IBoard['description'])
    PostCount = property(CheckingLastModifiedBTreeContainer.__len__)

    id, containerId = _containerIds_from_parent()

    sharingTargets = ()

    @property
    def mostRecentReply(self):
        """
        This is different than NewestDescendent in that it
        returns the most recent top-level comment of a topic.
        """
        generator = (x for x in self.values() if getattr(x, 'inReplyTo', None) is None)
        top_level_replies = sorted(generator,
                                   key=lambda x: getattr(x, 'createdTime', 0),
                                   reverse=True)
        return top_level_replies and top_level_replies[0]

    @property
    def NewestDescendantCreatedTime(self):
        post = self.NewestDescendant
        if post is not None:
            return post.createdTime
        return 0.0

    _newestPostWref = None

    # TODO: We probably need something to resolve conflicts here;
    # We always want the reference to the newest object to be what
    # is stored.
    # In order to do that we will probably want to make the ref into
    # its own persistent object (which should then be inside a
    # PersistentPropertyHolder).
    # Either that or we take _newestPostWref out of the object state entirely, as
    # we did with the Forum object...
    # If we arranged for our INameChooser to always choose names in increasing order,
    # we could simply use the object at the maxKey of the underlying BTree.
    # (But that conflicts with the goal of spreading the writes around to different buckets
    # ---and thus hopefully reducing overall conflicts---through choosing widely varying keys.)
    def _get_NewestPost(self):
        if self._newestPostWref is None and self.PostCount:
            # Lazily finding one
            newest_created = -1
            newest_post = None
            for post in self.values():
                if post.createdTime > newest_created:
                    newest_post = post
                    newest_created = post.createdTime
            if newest_post is not None:
                self.NewestDescendant = newest_post

        return self._newestPostWref() if self._newestPostWref is not None else None

    def _set_NewestPost(self, post):
        self._newestPostWref = IWeakRef(post)
    NewestDescendant = property(_get_NewestPost, _set_NewestPost)


@interface.implementer(ITopic, IAttributeAnnotatable)
class Topic(_AbstractUnsharedTopic, AbstractReadableSharedWithMixin):
    pass


@component.adapter(IPost, IIntIdAddedEvent)
def _post_added_to_topic(post, _):
    """
    Watch for a post to be added to a topic and keep track of the
    creation time of the latest post.

    The ContainerModifiedEvent does not give us the object (post)
    and it also can't tell us if the post was added or removed.
    """

    if ITopic.providedBy(post.__parent__):
        post.__parent__.NewestDescendant = post


@interface.implementer(IHeadlineTopic)
class HeadlineTopic(Topic):

    headline = AcquisitionFieldProperty(IHeadlineTopic['headline'])
    publishLastModified = None

    def _did_modify_publication_status(self, oldSharingTargets):
        """
        Fire off a modified event when the publication status changes.
        The event notes the sharing has changed.
        """

        newSharingTargets = set(self.sharingTargets)
        if newSharingTargets == oldSharingTargets:
            # No actual modification happened
            return

        provides = interface.providedBy(self)
        attributes = []
        for attr_name in 'sharedWith', 'sharingTargets':
            attr = provides.get(attr_name)
            if attr:
                iface_providing = attr.interface
                attributes.append(lifecycleevent.Attributes(
                    iface_providing, attr_name))

        event = ObjectSharingModifiedEvent(self, *attributes, 
                                           oldSharingTargets=oldSharingTargets)
        notify(event)

        # Ordinarily, we don't need to dispatch to sublocations a change
        # in the parent (hence why it is not a registered listener).
        # But here we know that the sharing is propagated automatically
        # down, so we do.
        dispatchToSublocations(self, event)

    def publish(self, *unused_args, **unused_kwargs):
        """
        Causes an ObjectSharingModifiedEvent to be fired if sharing changes.
        """
        if IDefaultPublished.providedBy(self):
            return

        oldSharingTargets = set(self.sharingTargets)
        interface.alsoProvides(self, IDefaultPublished)

        self.publishLastModified = time.time()
        self._did_modify_publication_status(oldSharingTargets)

    def unpublish(self, *unused_args, **unused_kwargs):
        """
        Causes an ObjectSharingModifiedEvent to be fired if sharing changes.
        """
        if not IDefaultPublished.providedBy(self):
            return

        oldSharingTargets = set(self.sharingTargets)
        interface.noLongerProvides(self, IDefaultPublished)
        self._did_modify_publication_status(oldSharingTargets)

    def is_published(self, *unused_args, **unused_kwargs):
        return IDefaultPublished.providedBy(self)
    isPublished = is_published


@interface.implementer(IGeneralTopic)
class GeneralTopic(Topic):
    pass


@interface.implementer(IGeneralHeadlineTopic)
class GeneralHeadlineTopic(AbstractDefaultPublishableSharedWithMixin,
                           GeneralTopic,
                           HeadlineTopic,
                           _CreatedNamedNTIIDMixin):
    headline = AcquisitionFieldProperty(IGeneralHeadlineTopic['headline'])

    _ntiid_type = NTIID_TYPE_GENERAL_TOPIC
    _ntiid_include_parent_name = True


from nti.dataserver.contenttypes.forums.interfaces import can_read


@interface.implementer(ICommunityHeadlineTopic)
class CommunityHeadlineTopic(GeneralHeadlineTopic):
    # Note: This used to extend (AbstractDefaultPublishableSharedWithMixin,GeneralHeadlineTopic)
    # in that order. But AbstractDefaultPublishableSharedWithMixin is already a base
    # class of GeneralHeadlineTopic, so there should be no need to move it to the front
    # again. By doing so, we create a situation where PyPy complained:
    # "TypeError: cycle among base classes: AbstractDefaultPublishableSharedWithMixin
    # < GeneralHeadlineTopic < AbstractDefaultPublishableSharedWithMixin"
    # No tests break if we remove the extra mention, and there should be no persistence issues as it's just
    # a mixin.
    mimeType = None

    _ntiid_type = NTIID_TYPE_COMMUNITY_TOPIC

    @CachedProperty('__parent__')
    def _community(self):
        """
        Return the community we are embedded in
        """
        # test legacy. Find community in lineage
        result = find_interface(self, ICommunity, strict=False)
        if result is None:
            # for new objects (e.g. new style courses)
            # find a creator that is a community in the lineage
            __traceback_info__ = self
            lineage = ILocationInfo(self).getParents()
            lineage.insert(0, self)
            for item in lineage:
                creator = getattr(item, 'creator', None)
                if creator is not None and ICommunity.providedBy(creator):
                    result = creator
                    break
        return result

    @readproperty
    def _ntiid_creator_username(self):
        """
        The community, not the user
        """
        community = self._community
        if community is not None:
            return community.username

    @property
    def sharingTargetsWhenPublished(self):
        # HACK: We need to check the of the community forum has an ACL
        # if so then share the note with the entities that can read the forum
        # This ACL must be static.
        # TODO: Remove hack
        _forum = self.__parent__

        possible_entities = set()

        # TODO: REMOVE IACL
        # By explicitly setting these ACL entities in the sharedWith, we
        # expose these objects as notable, which is wanted in (all?) cases.
        if IACLEnabled.providedBy(_forum):
            # don't include the creator of the forum if we have a ACL
            for ace in _forum.ACL:
                for action, entity, perm in ace:
                    if action == ACE_ACT_ALLOW and can_read(perm):
                        possible_entities.add(entity)
        elif IACLProvider.providedBy(_forum):
            for ace in IACLProvider(_forum).__acl__:
                if IACE.providedBy(ace):
                    action = ace.action
                    if action == ACE_ACT_ALLOW:
                        possible_entities.add(IPrincipal(ace.actor).id)

        if possible_entities:
            result = []
            for entity in possible_entities:
                entity = Entity.get_entity(entity)
                if entity is not None:
                    result.append(entity)
            return result

        # Instead of returning the default set from super, which would return
        # the dynamic memberships of the *creator* of this object, we
        # restrict it to the community in which we are embedded
        return [self._community] if self._community else ()


@interface.implementer(IDFLHeadlineTopic)
class DFLHeadlineTopic(GeneralHeadlineTopic):  # order matters

    mimeType = None

    _ntiid_type = NTIID_TYPE_DFL_TOPIC

    @CachedProperty('__parent__')
    def _dfl(self):
        """
        Return the DFL we are embedded in
        """
        # Find DFL in lineage
        result = find_interface(
            self, IDynamicSharingTargetFriendsList, strict=False)
        return result

    @readproperty
    def _ntiid_creator_username(self):
        intids = component.queryUtility(IIntIds)
        if intids is not None and self._dfl:
            result = intids.queryId(self._dfl)
            return str(result) if result is not None else None

    @property
    def sharingTargetsWhenPublished(self):
        return [self._dfl] if self._dfl else ()


def _forward_not_published(name):
    def f(self, *args, **kwargs):
        if IDefaultPublished.providedBy(self):
            return  # ignored
        getattr(self._sharing_storage, name)(*args, **kwargs)
    return f


@interface.implementer(IPersonalBlogEntry)
class PersonalBlogEntry(AbstractDefaultPublishableSharedWithMixin,
                        HeadlineTopic,
                        _CreatedNamedNTIIDMixin):
    creator = None
    headline = AcquisitionFieldProperty(IPersonalBlogEntry['headline'])
    mimeType = None

    _ntiid_type = NTIID_TYPE_PERSONAL_BLOG_ENTRY

    def __init__(self, *args, **kwargs):
        super(PersonalBlogEntry, self).__init__(*args, **kwargs)
        # JAM: Why didn't I put this at the class level?
        interface.alsoProvides(self, IWritableShared)

    def __setstate__(self, state):
        # TODO: A migration
        super(PersonalBlogEntry, self).__setstate__(state)
        if      not IDefaultPublished.providedBy(self) \
            and not IWritableShared.providedBy(self):
            interface.alsoProvides(self, IWritableShared)

    # We use this object to implement sharing storage when we are not published
    @Lazy
    def _sharing_storage(self):
        result = ShareableMixin()
        self._p_changed = True
        return result

    def publish(self, *args, **kwargs):
        # By also matching the state of IWritableShared, our
        # external updater automatically does the right thing and
        # doesn't even call us
        if IWritableShared.providedBy(self):
            interface.noLongerProvides(self, IWritableShared)

        super(PersonalBlogEntry, self).publish(*args, **kwargs)
        # NOTE: The order of this is weird. We need to capture
        # and broadcast the ObjectSharingModifiedEvent with the current
        # sharing targets /before/ we clear out anything set specifically
        # on us. This has the side-effect of causing the event listeners
        # to see an IWritableShared object, so we remove that first

        # When we publish, we wipe out any sharing data we used to have
        if '_sharing_storage' in self.__dict__:
            self._sharing_storage.clearSharingTargets()

    def unpublish(self, *args, **kwargs):
        # See notes in publish() for why we do this first
        interface.alsoProvides(self, IWritableShared)
        super(PersonalBlogEntry, self).unpublish(*args, **kwargs)

    def is_published(self, *unused_args, **unused_kwargs):
        return not IWritableShared.providedBy(self)
    isPublished = is_published

    updateSharingTargets = _forward_not_published('updateSharingTargets')
    clearSharingTargets = _forward_not_published('clearSharingTargets')
    addSharingTarget = _forward_not_published('addSharingTarget')

    def _may_have_sharing_targets(self):
        if not IDefaultPublished.providedBy(self):
            self._p_activate()
            return '_sharing_storage' in self.__dict__ and \
                self._sharing_storage._may_have_sharing_targets()
        return super(PersonalBlogEntry, self)._may_have_sharing_targets()

    @property
    def _non_published_sharing_targets(self):
        self._p_activate()
        if '_sharing_storage' in self.__dict__:
            return self._sharing_storage.sharingTargets
        return ()


@component.adapter(IHeadlineTopic)
class HeadlineTopicSublocations(ContainerSublocations):
    """
    Headline topics contain their children and also their story.
    """

    def sublocations(self):
        for x in super(HeadlineTopicSublocations, self).sublocations():
            yield x
        story = self.container.headline
        if story is not None:
            yield story


@component.adapter(IPersonalBlog)
@interface.implementer(INameChooser)
class PersonalBlogEntryNameChooser(AbstractNTIIDSafeNameChooser):
    """
    Handles NTIID-safe name choosing for an entry in a blog.
    """
    leaf_iface = IPersonalBlog


@component.adapter(IGeneralForum)
@interface.implementer(INameChooser)
class GeneralForumEntryNameChooser(AbstractNTIIDSafeNameChooser):
    """
    Handles NTIID-safe name choosing for an general forum entries.
    """
    leaf_iface = IGeneralForum
