#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Indexing metadata about most objects.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import BTrees

# disable 'redefining builtin id' because
# we get that from superclass
# pylint: disable=redefined-builtin
import six
from zope import component
from zope import interface

from zope.mimetype.interfaces import IContentTypeAware

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.base._compat import text_

from nti.chatserver.interfaces import IMessageInfo

from nti.coremetadata.interfaces import IX_LASTSEEN_TIME

from nti.coremetadata.interfaces import IMentionable

from nti.dataserver.contenttypes.forums.interfaces import ICommentPost
from nti.dataserver.contenttypes.forums.interfaces import IHeadlinePost
from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlogEntryPost

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDevice
from nti.dataserver.interfaces import ICreatedTime
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import ILastModified
from nti.dataserver.interfaces import IModeledContent
from nti.dataserver.interfaces import IUserGeneratedData
from nti.dataserver.interfaces import IUserTaggedContent
from nti.dataserver.interfaces import IDeletedObjectPlaceholder
from nti.dataserver.interfaces import IContained as INTIContained
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.ntiids.ntiids import TYPE_OID
from nti.ntiids.ntiids import TYPE_UUID
from nti.ntiids.ntiids import TYPE_INTID
from nti.ntiids.ntiids import TYPE_MEETINGROOM
from nti.ntiids.ntiids import TYPE_NAMED_ENTITY

from nti.ntiids.ntiids import is_ntiid_of_types
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.threadable.interfaces import IThreadable
from nti.threadable.interfaces import IInspectableWeakThreadable

from nti.zope_catalog.catalog import DeferredCatalog

from nti.zope_catalog.index import NormalizationWrapper
from nti.zope_catalog.index import SetIndex as RawSetIndex
from nti.zope_catalog.index import ValueIndex as RawValueIndex
from nti.zope_catalog.index import AttributeValueIndex as ValueIndex
from nti.zope_catalog.index import IntegerValueIndex as RawIntegerValueIndex

from nti.zope_catalog.topic import TopicIndex
from nti.zope_catalog.topic import ExtentFilteredSet

from nti.zope_catalog.datetime import TimestampToNormalized64BitIntNormalizer

from nti.zope_catalog.index import AttributeKeywordIndex

from nti.zope_catalog.interfaces import IDeferredCatalog

from nti.zope_catalog.string import StringTokenNormalizer

#: The name of the utility that the Zope Catalog
#: should be registered under
CATALOG_NAME = 'nti.dataserver.++etc++metadata-catalog'

logger = __import__('logging').getLogger(__name__)


class ValidatingMimeType(object):

    __slots__ = ('mimeType',)

    def __init__(self,  obj, unused_default=None):
        for proxy in (obj, IContentTypeAware(obj, None)):
            mimeType = getattr(proxy, 'mimeType', None) \
                    or getattr(proxy, 'mime_type', None)
            if mimeType:
                self.mimeType = mimeType
                break

    def __reduce__(self):
        raise TypeError()


class MimeTypeIndex(ValueIndex):
    default_field_name = 'mimeType'
    default_interface = ValidatingMimeType


class ValidatingContainerId(object):
    """
    The "interface" we adapt to to find the container id.

    Rejects certain types of contained IDs from being indexed
    by returning a None value:

    * OID container IDs. These are seen on MessageInfo objects,
      and, as they are always unique, are not helpful to index.
      Likewise for UUID and INTIDs, although in practice these
      are not yet used.

      We make an exception for forum comments, which we do index
      even if they have an excluded type for a container id. This is
      because some forums, notably those associated with classes,
      may not have better NTIIDs (yet), and we need these in the index
      for notabledata to work (see ``_only_included_comments_in_my_topics_ntiids``).
    """

    __slots__ = ('containerId',)

    _IGNORED_TYPES = {TYPE_OID, TYPE_UUID, TYPE_INTID}

    def __init__(self, obj, default):
        contained = INTIContained(obj, default)
        if contained is not None:
            cid = contained.containerId
            if      is_ntiid_of_types(cid, self._IGNORED_TYPES) \
                and not ICommentPost.providedBy(obj) \
                and not IMessageInfo.providedBy(obj):
                self.containerId = None
            else:
                self.containerId = text_(cid)

    def __reduce__(self):
        raise TypeError()


class ContainerIdIndex(ValueIndex):
    default_field_name = 'containerId'
    default_interface = ValidatingContainerId


# Will we use that with a string token normalizer?
# How to index creators? username? and just really
# hope that when a user is deleted the right events
# fire to remove all the indexed objects?
class ValidatingCreatedUsername(object):

    __slots__ = ('creator_username',)

    def __init__(self,  obj, unused_default=None):
        # Don't want to index user objects.
        if IUser.providedBy(obj):
            return
        try:
            creator = obj.creator
            username = getattr(creator, 'username', creator)
            username = getattr(username, 'id', username)
            if isinstance(username, six.string_types):
                self.creator_username = username.lower()
        except (AttributeError, TypeError):
            pass

    def __reduce__(self):
        raise TypeError()


class CreatorRawIndex(RawValueIndex):
    pass


def CreatorIndex(family=BTrees.family64):
    # We will use that with a string token normalizer
    return NormalizationWrapper(field_name='creator_username',
                                interface=ValidatingCreatedUsername,
                                index=CreatorRawIndex(family=family),
                                normalizer=StringTokenNormalizer())


class SharedWithRawIndex(RawSetIndex):
    pass


def SharedWithIndex(family=BTrees.family64):
    # SharedWith is a mixin property, currently,
    # the interface it is defined on is not really
    # the one we want, therefore we just ask for it from
    # anyone
    return NormalizationWrapper(field_name='sharedWith',
                                normalizer=StringTokenNormalizer(),
                                index=SharedWithRawIndex(family=family),
                                is_collection=True)


class TaggedToRawIndex(RawSetIndex):
    pass


class TaggedTo(object):
    """
    The \"interface\" we adapt to in order to
    find entities that are tagged to by the object.

    We take anything that is :class:`.IUserTaggedContent`` and look inside the
    'tags' sequence defined by it. If we find something that looks
    like an NTIID for a named entity, we look up the entity, and if
    it exists, we return its NTIID or username: If the entity is globally
    named, then the username is returned, otherwise, if the entity is only
    locally named, the NTIID is returned.
    """

    __slots__ = ('context',)

    # Tags are normally lower cased, but depending on when we get called
    # it's vaguely possible that we might see an upper-case value?
    _ENTITY_TYPES = {TYPE_NAMED_ENTITY, TYPE_NAMED_ENTITY.lower(),
                     TYPE_MEETINGROOM, TYPE_MEETINGROOM.lower()}

    def __init__(self, context, unused_default):
        self.context = IUserTaggedContent(context, None)

    @property
    def tagged_usernames(self):
        if self.context is None:
            return ()

        raw_tags = self.context.tags
        # Most things don't have tags
        if not raw_tags:
            return ()

        username_tags = set()
        for raw_tag in raw_tags:  # pylint: disable=not-an-iterable
            if is_ntiid_of_types(raw_tag, self._ENTITY_TYPES):
                entity = find_object_with_ntiid(raw_tag)
                if entity is not None:
                    # We actually have to be a bit careful here; we only want
                    # to catch certain types of entity tags, those that are either
                    # to an individual or those that participate in security
                    # relationships; (e.g., it doesn't help to use a regular FriendsList
                    # since that is effectively flattened).
                    # Currently, this abstraction doesn't exactly exist so we
                    # are very specific about it. See also :mod:`sharing`
                    if IUser.providedBy(entity):
                        username_tags.add(entity.username)
                    elif IDynamicSharingTargetFriendsList.providedBy(entity):
                        username_tags.add(entity.NTIID)
        return username_tags


def TaggedToIndex(family=BTrees.family64):
    """
    Indexes the NTIIDs of entities mentioned in tags.
    """
    return NormalizationWrapper(field_name='tagged_usernames',
                                normalizer=StringTokenNormalizer(),
                                index=TaggedToRawIndex(family=family),
                                interface=TaggedTo,
                                is_collection=True)


class MentionedRawIndex(RawSetIndex):
    pass


class Mentioned(object):
    """
    The \"interface\" we adapt to in order to
    find entities that are mentioned to by the object.

    We take anything that is :class:`.IMentionable`` and look inside the
    'mentions' sequence defined by it.

    TODO: This may eventually replace the TaggedTo index in the future,
     but currently supports only usernames, and does not affect
     sharing/permissions.  Will need to decide how to handle those issues
     first.
    """

    __slots__ = ('context',)

    def __init__(self, context, unused_default):
        self.context = IMentionable(context, None)

    @property
    def mentioned_usernames(self):
        if self.context is None:
            return ()

        raw_mentions = self.context.mentions
        # Most things don't have mentions
        if not raw_mentions:
            return ()

        return set(raw_mentions)


def MentionedIndex(family=BTrees.family64):
    """
    Indexes the usernames of entities mentioned in IMentionable objects.
    """
    return NormalizationWrapper(field_name='mentioned_usernames',
                                normalizer=StringTokenNormalizer(),
                                index=MentionedRawIndex(family=family),
                                interface=Mentioned,
                                is_collection=True)


class CreatorOfInReplyToRawIndex(RawValueIndex):
    pass


class CreatorOfInReplyTo(object):
    """
    The 'interface' we use to find the creator
    name an object is in reply-to.
    """

    __slots__ = ('context',)

    def __init__(self, context, unused_default):
        self.context = context

    @property
    def creator_name_replied_to(self):
        try:
            return ValidatingCreatedUsername(self.context.inReplyTo).creator_username
        except (TypeError, AttributeError):
            return None

    def __reduce__(self):
        raise TypeError()


def CreatorOfInReplyToIndex(family=BTrees.family64):
    """
    Indexes all the replies to a particular user
    """
    return NormalizationWrapper(field_name='creator_name_replied_to',
                                normalizer=StringTokenNormalizer(),
                                index=CreatorOfInReplyToRawIndex(
                                    family=family),
                                interface=CreatorOfInReplyTo)


def isTopLevelContentObjectFilter(unused_extent, unused_docid, document):
    # This is messy  !!!
    # NOTE: This is referenced by persistent objects, must stay
    if getattr(document, '__is_toplevel_content__', False):
        return True

    if IModeledContent.providedBy(document):
        if IFriendsList.providedBy(document) or IDevice.providedBy(document):
            # These things are modeled content, for some reason
            return False

        if IPersonalBlogEntryPost.providedBy(document):
            return bool(document.sharedWith)
        # HeadlinePosts (which are IMutedInStream) are threadable,
        # but we don't consider them top-level. (At this writing,
        # we don't consider the containing Topic to be top-level
        # either, because it isn't IModeledContent.)
        elif IHeadlinePost.providedBy(document):
            return False

        if IInspectableWeakThreadable.providedBy(document):
            return not document.isOrWasChildInThread()

        if IThreadable.providedBy(document):
            return document.inReplyTo is None
        return True
    # Only modeled content; anything else is not


class TopLevelContentExtentFilteredSet(ExtentFilteredSet):
    """
    A filter for a topic index that collects top-level objects.
    """

    def __init__(self, fid, family=BTrees.family64):
        super(TopLevelContentExtentFilteredSet, self).__init__(fid,
                                                               isTopLevelContentObjectFilter,
                                                               family=family)


def isDeletedObjectPlaceholder(unused_extent, unused_docid, document):
    # NOTE: This is referenced by persistent objects, must stay.
    return IDeletedObjectPlaceholder.providedBy(document)


class DeletedObjectPlaceholderExtentFilteredSet(ExtentFilteredSet):
    """
    A filter for a topic index that collects deleted placeholders.
    """

    def __init__(self, fid, family=BTrees.family64):
        super(DeletedObjectPlaceholderExtentFilteredSet, self).__init__(fid,
                                                                        isDeletedObjectPlaceholder,
                                                                        family=family)


def isUserGeneratedData(unused_extent, unused_docid, document):
    # NOTE: This is referenced by persistent objects, must stay.
    return IUserGeneratedData.providedBy(document)


class IsUserGeneratedDataExtentFilteredSet(ExtentFilteredSet):
    """
    A filter for a topic index that collects user generated data objects.
    """

    def __init__(self, fid, family=BTrees.family64):
        super(IsUserGeneratedDataExtentFilteredSet, self).__init__(fid,
                                                                   isUserGeneratedData,
                                                                   family=family)


class CreatedTimeRawIndex(RawIntegerValueIndex):
    pass


def CreatedTimeIndex(family=BTrees.family64):
    return NormalizationWrapper(field_name='createdTime',
                                interface=ICreatedTime,
                                index=CreatedTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class LastModifiedRawIndex(RawIntegerValueIndex):
    pass


def LastModifiedIndex(family=BTrees.family64):
    return NormalizationWrapper(field_name='lastModified',
                                interface=ILastModified,
                                index=LastModifiedRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())


class RevSharedWith(object):

    __slots__ = ('context',)

    def __init__(self, context, unused_default=None):
        self.context = context

    @property
    def usernames(self):
        result = getattr(self.context, 'sharedWith', None)
        return None if not result else result


def RevSharedWithIndex(family=BTrees.family64):
    return AttributeKeywordIndex(field_name='usernames',
                                 interface=RevSharedWith,
                                 family=family)


class LastSeenTimeRawIndex(RawIntegerValueIndex):
    pass


def LastSeenTimeIndex(family=BTrees.family64):
    return NormalizationWrapper(field_name='lastSeenTime',
                                interface=IUser,
                                index=LastSeenTimeRawIndex(family=family),
                                normalizer=TimestampToNormalized64BitIntNormalizer())



IX_TOPICS = 'topics'
IX_CREATOR = 'creator'
IX_MIMETYPE = 'mimeType'
IX_TAGGEDTO = 'taggedTo'
IX_MENTIONED = 'mentioned'
IX_SHAREDWITH = 'sharedWith'
IX_CONTAINERID = 'containerId'
IX_CREATEDTIME = 'createdTime'
IX_LASTMODIFIED = 'lastModified'
IX_REVSHAREDWITH = 'revSharedWith'
IX_REPLIES_TO_CREATOR = 'repliesToCreator'

#: The name of the topic/group in the topics index
#: that stores top-level content.
#: See :class:`TopLevelContentExtentFilteredSet`
TP_TOP_LEVEL_CONTENT = 'topLevelContent'

#: The name of the topic/group in the topics index
#: that stores deleted placeholders.
#: See :class:`DeletedObjectPlaceholderExtentFilteredSet`
TP_DELETED_PLACEHOLDER = 'deletedObjectPlaceholder'

#: See :class:`IUserGeneratedData`
TP_USER_GENERATED_DATA = 'isUserGeneratedData'


@interface.implementer(IDeferredCatalog)
class MetadataCatalog(DeferredCatalog):

    family = BTrees.family64

    def force_index_doc(self, docid, ob):  # BWC
        self.index_doc(docid, ob)


def get_metadata_catalog(registry=component):
    catalog = registry.queryUtility(IDeferredCatalog, name=CATALOG_NAME)
    return catalog


def add_catalog_filters(catalog, family=BTrees.family64):
    topic_index = catalog[IX_TOPICS]
    for filter_id, factory in ((TP_TOP_LEVEL_CONTENT, TopLevelContentExtentFilteredSet),
                               (TP_USER_GENERATED_DATA, IsUserGeneratedDataExtentFilteredSet),
                               (TP_DELETED_PLACEHOLDER, DeletedObjectPlaceholderExtentFilteredSet)):
        the_filter = factory(filter_id, family=family)
        topic_index.addFilter(the_filter)
    return catalog


def create_metadata_catalog(catalog=None, family=BTrees.family64):
    if catalog is None:
        catalog = MetadataCatalog(family=family)

    for name, clazz in ((IX_TOPICS, TopicIndex),
                        (IX_CREATOR, CreatorIndex),
                        (IX_MIMETYPE, MimeTypeIndex),
                        (IX_TAGGEDTO, TaggedToIndex),
                        (IX_MENTIONED, MentionedIndex),
                        (IX_SHAREDWITH, SharedWithIndex),
                        (IX_CONTAINERID, ContainerIdIndex),
                        (IX_CREATEDTIME, CreatedTimeIndex),
                        (IX_LASTSEEN_TIME, LastSeenTimeIndex),
                        (IX_LASTMODIFIED, LastModifiedIndex),
                        (IX_REVSHAREDWITH, RevSharedWithIndex),
                        (IX_REPLIES_TO_CREATOR, CreatorOfInReplyToIndex)):
        index = clazz(family=family)
        locate(index, catalog, name)
        catalog[name] = index

    add_catalog_filters(catalog, family)
    return catalog


def install_metadata_catalog(site_manager_container, intids=None):
    """
    Installs the global metadata catalog.
    """
    lsm = site_manager_container.getSiteManager()
    intids = lsm.getUtility(IIntIds) if intids is None else intids
    catalog = get_metadata_catalog(registry=lsm)
    if catalog is not None:
        return catalog

    catalog = create_metadata_catalog(family=intids.family)
    locate(catalog, site_manager_container, CATALOG_NAME)
    intids.register(catalog)
    lsm.registerUtility(catalog,
                        provided=IDeferredCatalog,
                        name=CATALOG_NAME)

    for index in catalog.values():
        intids.register(index)
    return catalog
