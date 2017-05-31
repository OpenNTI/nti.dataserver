#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from array import array

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import CachedProperty

from zope.intid.interfaces import IIntIds

from BTrees.OOBTree import Set
from BTrees.LFBTree import LFSet

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.notabledata.interfaces import IUserNotableData
from nti.app.notabledata.interfaces import IUserNotableProvider
from nti.app.notabledata.interfaces import IUserNotableDataStorage

from nti.dataserver.authentication import dynamic_memberships_that_participate_in_security

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.metadata.index import IX_TOPICS
from nti.dataserver.metadata.index import IX_TAGGEDTO
from nti.dataserver.metadata.index import IX_CREATEDTIME
from nti.dataserver.metadata.index import TP_TOP_LEVEL_CONTENT
from nti.dataserver.metadata.index import TP_DELETED_PLACEHOLDER

from nti.dataserver.metadata.index import get_metadata_catalog
        
from nti.dataserver.users.interfaces import IUserProfile

from nti.externalization.oids import to_external_ntiid_oid

from nti.invitations.utils import get_pending_invitation_ids

from nti.property.property import annotation_alias

from nti.zope_catalog.catalog import ResultSet

_BLOG_ENTRY_NTIID = "tag:nextthought.com,2011-10:%s-Topic:PersonalBlogEntry"
_BLOG_ENTRY_MIMETYPE = "application/vnd.nextthought.forums.personalblogentry"
_BLOG_COMMENT_MIMETYPE = "application/vnd.nextthought.forums.personalblogcomment"
_BLOG_ENTRY_POST_MIMETYPE = "application/vnd.nextthought.forums.personalblogentrypost"

_DFL_TOPIC_MIMETYPE = "application/vnd.nextthought.forums.dflheadlinetopic"
_TOPIC_MIMETYPE = "application/vnd.nextthought.forums.communityheadlinetopic"
_TOPIC_COMMENT_MYMETYPE = "application/vnd.nextthought.forums.generalforumcomment"

_MESSAGEINFO_MYMETYPE = "application/vnd.nextthought.messageinfo"


class SafeResultSet(ResultSet):

    def __init__(self, uids, uidutil, *args, **kwargs):
        ResultSet.__init__(self, uids, uidutil, True)

_SafeResultSet = SafeResultSet  # BWC


@interface.implementer(IUserNotableData)
@component.adapter(IUser, interface.Interface)
class UserNotableData(AbstractAuthenticatedView):

    def __init__(self, context, request):
        AbstractAuthenticatedView.__init__(self, request)
        self.remoteUser = context
        self._time_range = (None, None)

    def __reduce__(self):
        raise TypeError()

    @CachedProperty
    def _intids(self):
        return component.getUtility(IIntIds)

    @CachedProperty
    def _catalog(self):
        return get_metadata_catalog()

    @CachedProperty
    def _notable_storage(self):
        return IUserNotableDataStorage(self.remoteUser)

    def __find_blog_comment_intids(self):
        # We know that blog comments have a container ID that is the
        # blog entry's NTIID. We know that the blog entry's NTIID is deterministic
        # and boundable (we know the beginning and we can put an entry
        # that is exactly after the last possible NTIID we would generate, and
        # yet still before any other NTIID we would generate). So we first get all
        # the blog NTIIDs, then we find things that use them as containers and which
        # are comments (actually, we skip that last step; we know the only things
        # that can be contained are the headline post and comments, and the headline
        # post will be filtered out automatically because we created it).

        # The base ntiid. Real ntiids will start with this, followed by a -
        min_ntiid = _BLOG_ENTRY_NTIID % self.remoteUser.username
        # the . character is the next one after the -
        max_ntiid = min_ntiid + '.'

        container_id_idx = self._catalog['containerId']
        docids = container_id_idx.apply({'between': (min_ntiid, max_ntiid)})
        container_ids = {
            container_id_idx.documents_to_values[x] for x in docids
        }

        return container_id_idx.apply({'any_of': container_ids})

    @CachedProperty
    def _all_my_pending_invitations_intids(self):
        username = self.remoteUser.username
        email = getattr(IUserProfile(self.remoteUser, None), 'email', None)
        return get_pending_invitation_ids(receivers=(username, email))

    @CachedProperty
    def _all_blog_comment_intids(self):
        query = {'any_of': (_BLOG_COMMENT_MIMETYPE,)}
        return self._catalog['mimeType'].apply(query)

    @CachedProperty
    def _topics_created_by_me_intids(self):
        catalog = self._catalog
        topic_intids = catalog['mimeType'].apply(
            {'any_of': (_TOPIC_MIMETYPE,)})

        topics_created_by_me_intids = catalog.family.IF.intersection(topic_intids,
                                                                     self._intids_created_by_me)
        return topics_created_by_me_intids

    def __topic_ntiids(self, excluded_topic_oids=()):
        topic_ntiids = {
            x.NTIID or None for x in SafeResultSet(self._topics_created_by_me_intids, self._intids)
            if to_external_ntiid_oid(x) not in excluded_topic_oids
        }
        topic_ntiids.discard(None)
        return list(topic_ntiids)

    @CachedProperty
    def _all_comments_in_my_topics_intids(self):
        # Note that we're not doing a join to the Mime index, as only comments
        # should have this as a container id.
        __topic_ntiids = self.__topic_ntiids()
        query = {'any_of': __topic_ntiids}
        comments_in_my_topics_intids = self._catalog[
            'containerId'].apply(query)
        return comments_in_my_topics_intids

    @CachedProperty
    def _only_included_comments_in_my_topics_intids(self):
        excluded_topic_oids = self._not_notable_oids or ()
        if not excluded_topic_oids:
            return self._all_comments_in_my_topics_intids
        query = {'any_of': self.__topic_ntiids(excluded_topic_oids)}
        return self._catalog['containerId'].apply(query)

    def __find_generalForum_comment_intids(self):
        # Get the toplevel intids of comments created in a forum
        # that I own (created). There is not a very good way to do this,
        # sadly. Indexing NTIID is a poor choice because it's 1-to-1
        # The best we can seem to do is find all the forums I created,
        # manually get their NTIIDs,  get things that are in those containers
        # that are toplevel.
        # Once we do this, though, we mist still subtract things shared directly
        # to me that are in _all_comments_in_my_topics_intids but not in this
        # set, because of the way ACL sharing for community topics is implemented
        # (the instructor is explicitly in the sharingTargets list)
        return self._only_included_comments_in_my_topics_intids

    @CachedProperty
    def _topic_comment_intids_to_exclude(self):
        all_comments = self._all_comments_in_my_topics_intids
        included_comments = self._only_included_comments_in_my_topics_intids
        # Everything that's in all_comments, but not in included_comments
        comments_i_dont_want = self._catalog.family.IF.difference(all_comments,
                                                                  included_comments)
        return comments_i_dont_want

    @CachedProperty
    def _intids_created_by_me(self):
        query = {'any_of': (self.remoteUser.username,)}
        return self._catalog['creator'].apply(query)

    @CachedProperty('_time_range')
    def _intids_in_time_range(self):
        min_created_time, max_created_time = self._time_range
        if min_created_time is None and max_created_time is None:
            return None
        if min_created_time is None:
            # We should probably remove time range filtering here, and leave it
            # to callers. Batching from 0 to a timestamp is extremely slow as our
            # index increases in size. The entire index has to be awaken to do
            # the filtering.
            logger.warn('Slow running query from time 0 to %s on large index.',
                        max_created_time)

        query = {'between': (min_created_time, max_created_time)}
        intids_in_time_range = self._catalog[IX_CREATEDTIME].apply(query)
        return intids_in_time_range

    @CachedProperty
    def _group_ntiids(self):
        # Return all friends list we own or are members of.
        results = (set(self.remoteUser.friendsLists.values()) |
                   set(self.remoteUser.dynamic_memberships))
        return {x.NTIID for x in results if IFriendsList.providedBy(x)}

    @CachedProperty('_time_range')
    def _safely_viewable_notable_intids(self):
        catalog = self._catalog
        # Any top-level items shared directly to me or my groups
        shared_with_ids = self._group_ntiids
        shared_with_ids.add(self.remoteUser.username)
        query = {'any_of': shared_with_ids}
        intids_shared_to_me = catalog['sharedWith'].apply(query)

        toplevel_intids_extent = catalog[IX_TOPICS][
            TP_TOP_LEVEL_CONTENT].getExtent()
        toplevel_intids_shared_to_me = toplevel_intids_extent.intersection(
            intids_shared_to_me)

        # Blog posts are now top-level, exclude them. It's confusing when both
        # blogs and blog-posts are returned.
        query = {'any_of': (_BLOG_ENTRY_POST_MIMETYPE,)}
        blog_post_intids = catalog['mimeType'].apply(query)
        toplevel_intids_shared_to_me = catalog.family.IF.difference(toplevel_intids_shared_to_me,
                                                                    blog_post_intids)

        # Any topics shared to me or my groups
        topic_intids = catalog['mimeType'].apply({'any_of': (_TOPIC_MIMETYPE,
                                                             _DFL_TOPIC_MIMETYPE)})
        topic_intids = catalog.family.IF.intersection(topic_intids,
                                                      intids_shared_to_me)

        query = {'any_of': (self.remoteUser.username,)}
        intids_replied_to_me = catalog['repliesToCreator'].apply(query)

        intids_blog_comments = self.__find_blog_comment_intids()
        toplevel_intids_blog_comments = toplevel_intids_extent.intersection(
            intids_blog_comments)

        query = {'any_of': (_BLOG_ENTRY_MIMETYPE,)}
        blogentry_intids = catalog['mimeType'].apply(query)
        blogentry_intids_shared_to_me = catalog.family.IF.intersection(intids_shared_to_me,
                                                                       blogentry_intids)

        toplevel_intids_forum_comments = self.__find_generalForum_comment_intids()
        safely_viewable_intids = [toplevel_intids_shared_to_me,
                                  intids_replied_to_me,
                                  topic_intids,
                                  toplevel_intids_blog_comments,
                                  blogentry_intids_shared_to_me,
                                  toplevel_intids_forum_comments]

        self._notable_storage.add_intids(safely_viewable_intids, safe=True)

        safely_viewable_intids = catalog.family.IF.multiunion(
            safely_viewable_intids)
        if self._intids_in_time_range is not None:
            safely_viewable_intids = catalog.family.IF.intersection(self._intids_in_time_range,
                                                                    safely_viewable_intids)

        # Subtract any comments that crept in that I don't want
        safely_viewable_intids = catalog.family.IF.difference(safely_viewable_intids,
                                                              self._topic_comment_intids_to_exclude)
        return safely_viewable_intids

    @CachedProperty('_time_range')
    def _notable_intids(self):
        # TODO: See about optimizing this query plan. ZCatalog has a
        # CatalogPlanner object that we might could use.
        catalog = self._catalog
        toplevel_intids_extent = catalog[IX_TOPICS][
            TP_TOP_LEVEL_CONTENT].getExtent()
        deleted_intids_extent = catalog[IX_TOPICS][
            TP_DELETED_PLACEHOLDER].getExtent()

        # Things tagged to me or my security-aware dynamic memberships
        # XXX: This is probably slow? How many unions does this wind up doing?
        # it definitely slows down over time
        tagged_to_usernames_or_intids = {self.remoteUser.username}
        # Note the use of private API, a signal to cleanup soon
        for membership in dynamic_memberships_that_participate_in_security(self.remoteUser,
                                                                           as_principals=False):
            if IDynamicSharingTargetFriendsList.providedBy(membership):
                tagged_to_usernames_or_intids.add(membership.NTIID)

        query = {'any_of': tagged_to_usernames_or_intids}
        intids_tagged_to_me = catalog[IX_TAGGEDTO].apply(query)

        safely_viewable_intids = self._safely_viewable_notable_intids
        intids_by_priority_creators = LFSet()
        for provider in component.subscribers((self.remoteUser, self.request),
                                              IUserNotableProvider):
            intids_by_priority_creators.update(provider.get_notable_intids())

        # Top-level things by the instructors...
        toplevel_intids_by_priority_creators = toplevel_intids_extent.intersection(
            intids_by_priority_creators)

        # 2014-06-10 - ...taking out blog comments because that might be
        # confusing
        toplevel_intids_by_priority_creators = catalog.family.IF.difference(toplevel_intids_by_priority_creators,
                                                                            self._all_blog_comment_intids)

        # As-of fall 2014, auto-created topics are not created by the instuctor,
        # but instead a separate entity, so we want to return those too. In the past,
        # they were created by the instructor, which means that if you go far enough
        # back in notable data you'll find them (and at the time they were created, we
        # were explicitly excluding them)---but the benefit to knowing about new discussions
        # from the instructors outweighs any oddity from the old stuff.

        # Now any topics by our a-listers, but only non-excluded topics
        query = {'any_of': (_TOPIC_MIMETYPE,)}
        topic_intids = catalog['mimeType'].apply(query)
        topic_intids_by_priority_creators = catalog.family.IF.intersection(topic_intids,
                                                                           intids_by_priority_creators)

        # Sadly, to be able to provide the "TotalItemCount" we have to
        # apply security to all the intids not guaranteed to be
        # viewable; if we didn't have to do that we could imagine
        # doing so incrementally, as needed, on the theory that there
        # are probably more things shared directly with me or replied
        # to me than created by others that I happen to be able to see
        questionable_intids = [
            intids_tagged_to_me,
            topic_intids_by_priority_creators,
            toplevel_intids_by_priority_creators,
        ]
        self._notable_storage.add_intids(questionable_intids, safe=False)
        questionable_intids = catalog.family.IF.multiunion(questionable_intids)
        if self._intids_in_time_range is not None:
            questionable_intids = catalog.family.IF.intersection(self._intids_in_time_range,
                                                                 questionable_intids)

        uidutil = self._intids
        security_check = self.make_sharing_security_check()
        for questionable_uid in questionable_intids:
            if questionable_uid in safely_viewable_intids:
                continue
            questionable_obj = uidutil.queryObject(questionable_uid)
            if      questionable_obj is not None \
                    and security_check(questionable_obj):
                safely_viewable_intids.add(questionable_uid)

        # 2015-07-11 Subtract any message info
        query = {'any_of': (_MESSAGEINFO_MYMETYPE,)}
        messageinfo_intids = catalog['mimeType'].apply(query)
        safely_viewable_intids = catalog.family.IF.difference(safely_viewable_intids,
                                                              messageinfo_intids)

        # Make sure none of the stuff we created got in
        intids_created_by_me = self._intids_created_by_me
        safely_viewable_intids = catalog.family.IF.difference(safely_viewable_intids,
                                                              intids_created_by_me)

        # Make sure nothing that's deleted got in
        non_deleted_safely_viewable_intids = \
            (safely_viewable_intids - deleted_intids_extent)

        return non_deleted_safely_viewable_intids

    def get_notable_intids(self, min_created_time=None, max_created_time=None):
        self._time_range = (min_created_time, max_created_time)
        ids = self._notable_intids
        return ids

    def __len__(self):
        return len(self.get_notable_intids())

    def __bool__(self):
        if self._safely_viewable_notable_intids:
            return True
        return bool(len(self))
    __nonzero__ = __bool__

    def __iter__(self):
        return iter(SafeResultSet(self.get_notable_intids(), self._intids))

    def sort_notable_intids(self, notable_intids,
                            field_name='createdTime',
                            limit=None,
                            reverse=False,
                            reify=False):
        # Sorting returns a generator which is fine unless we need to get a length.
        # In many cases we don't so we let the caller decide
        _sorted = self._catalog[field_name].sort(notable_intids,
                                                 limit=limit,
                                                 reverse=reverse)
        if not reify:
            return _sorted

        # For large lists, an array is more memory efficient then a list,
        # since it uses native storage
        # Py3 porting issue, long went away?
        array_type = 'l' if isinstance(
            self._catalog.family.maxint, long) else 'i'
        return array(str(array_type), _sorted)

    def iter_notable_intids(self, notable_intids, ignore_missing=False):
        return SafeResultSet(notable_intids, self._intids)

    _KEY = 'nti.appserver.ugd_query_views._NotableUGDLastViewed'
    lastViewed = annotation_alias(_KEY, annotation_property='remoteUser', default=0,
                                  doc="LastViewed is stored as an annotation on the user")

    def is_object_notable(self, maybe_notable):
        # Tests with a Janux database snapshot seem to indicate that the intid
        # catalog queries are fast enough that this doesn't add much/any
        # overhead. The other end of the spectrum is to brute-force the
        # algorithm by hand.
        iid = self._intids.queryId(maybe_notable)
        if iid is None:
            return False

        notables = self._notable_intids
        return iid in notables

    _NKEY = 'nti.appserver.ugd_query_views._NotableUGD_ExcludedOIDs'
    _not_notable_oids = annotation_alias(_NKEY, annotation_property='remoteUser',
                                         doc="A set of OIDs to exclude (stored on the user)"
                                         "We use OID instead of intid to guard against re-use.")

    def object_is_not_notable(self, maybe_notable):
        # Right now, we only support this and check it for
        # forum objects
        if getattr(maybe_notable, 'mimeType', '') == _TOPIC_MIMETYPE:
            not_notable = self._not_notable_oids
            if not_notable is None:
                not_notable = self._not_notable_oids = Set()
            not_notable.add(to_external_ntiid_oid(maybe_notable))

from zope import lifecycleevent

from zope.annotation.factory import factory as an_factory

from zope.container.contained import Contained

from persistent import Persistent
from persistent.list import PersistentList


@component.adapter(IUser)
@interface.implementer(IUserNotableDataStorage)
class UserNotableDataStorage(Persistent, Contained):

    def __init__(self):
        pass

    @property
    def context(self):
        return self.__parent__

    @Lazy
    def _safe_intid_set(self):
        self._p_changed = True
        return self.context.family.IF.TreeSet()

    @Lazy
    def _unsafe_intid_set(self):
        self._p_changed = True
        return self.context.family.IF.TreeSet()

    @Lazy
    def _owned_objects(self):
        self._p_changed = True
        # We don't ever expect this to be very big
        return PersistentList()

    # Migration compatibility
    def values(self):
        if '_owned_objects' in self.__dict__:
            return self._owned_objects
        return ()

    def store_intid(self, intid, safe=False):
        s = self._safe_intid_set if safe else self._unsafe_intid_set
        added = s.add(intid)
        if added:
            return intid

    def store_object(self, obj, safe=False, take_ownership=False):
        # Note we directly access the intid attribute
        intids = component.queryUtility(IIntIds)
        attribute = getattr(intids, 'attribute', '_ds_intid')
        if take_ownership:
            if getattr(obj, attribute, None) is not None:
                # Programming error...somebody lost track of ownership
                raise ValueError("Object already registered")
            lifecycleevent.created(obj)
            assert getattr(obj, attribute, None) is None
            self._owned_objects.append(obj)
            if getattr(obj, '__parent__', None) is None:
                obj.__parent__ = self
            lifecycleevent.added(obj, self, str(len(self._owned_objects)))

        if getattr(obj, attribute, None) is None:
            raise ValueError("Object does not have intid")
        return self.store_intid(getattr(obj, attribute), safe=safe)

    def add_intids(self, ids, safe=False):
        """
        If we have intids for the given safety level, append them
        to the array. Optimization for the common case where
        we don't have one or the other to avoid creating expensive
        Set objects.
        """
        self._p_activate()
        s = '_safe_intid_set' if safe else '_unsafe_intid_set'
        if s in self.__dict__:  # has Lazy kicked in?
            ids.append(getattr(self, s))

UserNotableDataStorageFactory = an_factory(UserNotableDataStorage)
