#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time
import BTrees
import numbers
import warnings
import collections

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import Lazy

from zope.deprecation import deprecated

from zope.intid.interfaces import IIntIds

from zope.location.interfaces import ISublocations

from ZODB.interfaces import IConnection

from z3c.password.interfaces import IPasswordUtility

from persistent.list import PersistentList

from nti.apns.interfaces import IDeviceFeedbackEvent
from nti.apns.interfaces import INotificationService

from nti.containers.dicts import CaseInsensitiveLastModifiedDict

from nti.dataserver import sharing

from nti.dataserver.activitystream_change import Change

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IOpenIdUser
from nti.dataserver.interfaces import ITranscript
from nti.dataserver.interfaces import IFacebookUser
from nti.dataserver.interfaces import IIntIdIterable
from nti.dataserver.interfaces import INamedContainer
from nti.dataserver.interfaces import IContainerIterable
from nti.dataserver.interfaces import ITranscriptContainer
from nti.dataserver.interfaces import IDynamicSharingTarget
from nti.dataserver.interfaces import ITargetedStreamChangeEvent
from nti.dataserver.interfaces import IDataserverTransactionRunner
from nti.dataserver.interfaces import IDynamicSharingTargetFriendsList

from nti.dataserver.users.entity import get_shared_dataserver

from nti.dataserver.users.interfaces import OldPasswordDoesNotMatchCurrentPassword

from nti.dataserver.users.principal import Principal

from nti.datastructures.datastructures import ContainedStorage
from nti.datastructures.datastructures import AbstractNamedLastModifiedBTreeContainer

from nti.ntiids import ntiids

from nti.zodb import minmax
from nti.zodb import isBroken

# Starts as none, which matches what get_shared_dataserver takes as its
# clue to use get instead of query. But set to False or 0 to use
# query during evolutions.
BROADCAST_DEFAULT_DS = None

SharingTarget = sharing.SharingTargetMixin
deprecated('SharingTarget', 'Prefer sharing.SharingTargetMixin')

SharingSource = sharing.SharingSourceMixin
deprecated('SharingSource', 'Prefer sharing.SharingSourceMixin')

DynamicSharingTarget = sharing.DynamicSharingTargetMixin
deprecated('DynamicSharingTarget', 'Prefer sharing.DynamicSharingTargetMixin')

from nti.dataserver.users.communities import Everyone

from nti.dataserver.users.entity import NOOPCM as _NOOPCM

from nti.dataserver.users.friends_lists import FriendsList
from nti.dataserver.users.friends_lists import DynamicFriendsList
from nti.dataserver.users.friends_lists import _FriendsListMap  # BWC

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecated(
    "Import from nti.dataserver.users.communities.Community instead",
    Community='nti.dataserver.users.communities:Community')

zope.deferredimport.deprecatedFrom(
    "Moved to nti.dataserver.users.friends_lists",
    "nti.dataserver.users.friends_lists",
    "DynamicFriendsList",
    "_FriendsListUsernameIterable")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.dataserver.users.password",
    "nti.dataserver.users.password",
    "_Password")

ShareableMixin = sharing.ShareableMixin
deprecated('ShareableMixin', 'Prefer sharing.ShareableMixin')

from nti.dataserver.users.device import Device
from nti.dataserver.users.device import _DevicesMap


@interface.implementer(ITranscriptContainer)
class _TranscriptsMap(AbstractNamedLastModifiedBTreeContainer):
    contained_type = ITranscript
    container_name = u'Transcripts'
    __name__ = container_name


@interface.implementer(IContainerIterable,
                       IUser,
                       IIntIdIterable,
                       ISublocations)
class User(Principal):
    """A user is the central class for data storage. It maintains
    not only a few distinct pieces of data but also a collection of
    Contained items.

    All additions and deletions to Contained items
    go through the User class, which takes care of posting appropriate
    notifications to queues. For updates to contained objects,
    the methods beginUpdates() and endUpdates() must surround the updates. Objects
    retrieved from getObject() will be monitored for changes during this period
    and notifications posted at the end. Mutations to non-persistent data structurs
    may not be caught by this and so such objects should be explicitly marked
    as changed using setPersistentStateChanged().
    """

    family = BTrees.family64
    _ds_namespace = 'users'
    mime_type = 'application/vnd.nextthought.user'

    @classmethod
    def get_user(cls, username, dataserver=None, default=None):
        """
        Returns the User having ``username``, else None.

        :param basestring username: The username to find. Can also be an instance of
                this class, in which case it is immediately returned (effectively making this
                behave like a :mod:`zope.interface` cast. Note that it is this specific
                class, not :class:`User` in general.
        """
        if isinstance(username, cls):
            return username
        if username:
            result = cls.get_entity(username, dataserver=dataserver, default=default) 
        else:
            result = None
        # but this instance check is the base class
        return result if isinstance(result, User) else default

    @classmethod
    def create_user(cls, dataserver=None, **kwargs):
        """
        Creates (and returns) and places in the dataserver a new user,
        constructed using the keyword arguments given, the same as
        those the User constructor takes. Raises a :class:`KeyError`
        if the user already exists. You handle the transaction.
        """
        return cls.create_entity(dataserver=dataserver, **kwargs)

    delete_user = Principal.delete_entity

    # External incoming ignoring and accepting can arrive in three ways.
    # As a list, which replaces the entire contents.
    # As a single string, which is added to the list.
    # As a dictionary with keys 'add' and 'remove', mapping to lists

    @classmethod
    def _resolve_entities(cls, dataserver, external_object, value):
        result = []
        if isinstance(value, basestring):
            result = cls.get_entity(value, dataserver=dataserver)
        elif isinstance(value, collections.Sequence):
            # A list of names or externalized-entity maps
            result = []
            for username in value:
                if isinstance(username, collections.Mapping):
                    username = username.get('Username')
                entity = cls.get_entity(username, dataserver=dataserver)
                if entity:
                    result.append(entity)
        elif isinstance(value, collections.Mapping):
            if value.get('add') or value.get('remove'):
                # Specified edits
                result = {
                    'add': cls._resolve_entities(dataserver, external_object, value.get('add')),
                    'remove': cls._resolve_entities(dataserver, external_object, value.get('remove'))
                }
            else:
                # a single externalized entity map
                result = cls.get_entity(value.get('Username'), 
                                        dataserver=dataserver)

        return result

    __external_resolvers__ = {
        'ignoring': _resolve_entities, 
        'accepting': _resolve_entities
    }

    # The last login time is an number of seconds (as with time.time).
    # When it gets reset, the number of outstanding notifications also
    # resets. It is writable, number is not...
    lastLoginTime = minmax.NumericPropertyDefaultingToZero('lastLoginTime',
                                                           minmax.NumericMaximum,
                                                           as_number=True)
    # ...although, pending a more sophisticated notification tracking
    # mechanism, we are allowing notification count to be set...
    notificationCount = minmax.NumericPropertyDefaultingToZero('notificationCount',
                                                               minmax.MergingCounter)

    # TODO: If no AvatarURL is set when externalizing,
    # send back a gravatar URL for the primary email:
    # http://www.gravatar.com/avatar/%<Lowercase hex MD5>=44&d=mm

    def __init__(self, username, password=None,
                 parent=None, _stack_adjust=0):
        super(User, self).__init__(username, password=password, parent=parent)
        IUser['username'].bind(self).validate(self.username)
        # We maintain a Map of our friends lists, organized by
        # username (only one friend with a username)

        if self.__parent__ is None and component.queryUtility(IIntIds) is not None:
            warnings.warn(
                "No parent provided. User will have no Everyone list or Community; "
                "either use User.create_user or provide parent kwarg",
                stacklevel=(2 if type(self) == User else 3) + _stack_adjust)

        self.friendsLists = _FriendsListMap()
        self.friendsLists.__parent__ = self

        # Join our default community
        if self.__parent__:
            everyone = self.__parent__.get(Everyone._realname)
            if everyone:
                self.record_dynamic_membership(everyone)

        # We maintain a list of devices associated with this user
        # TODO: Want a persistent set?
        self.devices = _DevicesMap()
        self.devices.__parent__ = self

        # Create the containers, along with the initial set of contents.
        # Note that this doesn't reparent them, they stay parented by us
        # FIXME: We should be using a unique value for containerType (instead of
        # the generic CheckingLastModifiedBTreeContainer) so that we can
        # register adapters for these containers in a clean way.
        # FIXME: Why are we just using a dict instead of a btree implementation
        # for containersType? A user can (does) have many, many different
        # containers, so won't this pickle get too large?
        self.containers = ContainedStorage(create=self,
                                           containersType=CaseInsensitiveLastModifiedDict,
                                           containers={
                                                self.friendsLists.container_name: self.friendsLists,
                                                self.devices.container_name: self.devices})
        self.containers.__parent__ = self
        # TODO: This is almost certainly wrong. We hack around it
        self.containers.__name__ = ''

    def __setstate__(self, data):
        # Old objects might have a 'stream' of none? For no particular
        # reason?
        if isinstance(data, collections.Mapping) and 'stream' in data and data['stream'] is None:
            del data['stream']

        super(User, self).__setstate__(data)

    @property
    def creator(self):
        """ 
        For security, we are always our own creator.
        """
        return self

    @creator.setter
    def creator(self, unused_other):
        """ 
        Ignored. 
        """
        return

    @property
    def containerId(self):
        return u"Users"

    NTIID_TYPE = ntiids.TYPE_NAMED_ENTITY_USER

    def update_last_login_time(self):
        self.lastLoginTime = time.time()

    def updateFromExternalObject(self, parsed, *args, **kwargs):
        # with self._NoChangeBroadcast( self ):
        super(User, self).updateFromExternalObject(parsed, *args, **kwargs)
        updated = None
        lastLoginTime = parsed.pop('lastLoginTime', None)
        if isinstance(lastLoginTime, numbers.Number) and self.lastLoginTime < lastLoginTime:
            self.lastLoginTime = lastLoginTime
            # reset to zero. Note that we don't del the property to keep the
            # same persistent object object
            self.notificationCount = 0
            updated = True

        notificationCount = parsed.pop('NotificationCount', None)
        if isinstance(notificationCount, numbers.Number):
            self.notificationCount = notificationCount
            updated = True

        if 'password' in parsed:
            old_pw = None
            if self.has_password():
                # To change an existing password, you must send the old
                # password (The default, empty string, is never a valid password and lets
                # us produce better error messages then having no default)
                old_pw = parsed.pop('old_password', '')
                # And it must match
                if not self.password.checkPassword(old_pw):
                    raise OldPasswordDoesNotMatchCurrentPassword()
            password = parsed.pop('password')
            # TODO: Names/sites for these? That are distinct from the
            # containment structure?
            component.getUtility(IPasswordUtility).verify(password, old_pw)
            self.password = password  # NOTE: This re-verifies
            updated = True

        # Muting/Unmuting conversations. Notice that we only allow
        # a single thing to be changed at once. Also notice that we never provide
        # the full list of currently muted objects as external data. These
        # both support the idea that the use-case for this feature is a single button
        # in the UI at the conversation level, and that 'unmuting' a conversation is
        # only available /immediately/ after muting it, as an 'Undo' action (like in
        # gmail). Our muted conversations still show up in search results, as
        # in gmail.
        if 'mute_conversation' in parsed:
            self.mute_conversation(parsed.pop('mute_conversation'))
            updated = True
        elif 'unmute_conversation' in parsed:
            self.unmute_conversation(parsed.pop('unmute_conversation'))
            updated = True

        # See notes on how ignoring and accepting values may arrive.
        def handle_ext(reset, add, value):
            if value:
                updated = True
                for x in value:
                    reset(x)
                    add(x)

        def set_from_input(field, existing, remove):
            """
            Get our set from input. For targeted removes, go
            ahead and remove.
            """
            value = parsed.pop(field, None)
            result = None
            if isinstance(value, collections.Sequence):
                result = set(value)
            elif isinstance(value, collections.Mapping):
                result = set(existing)
                for x in (value.get('add') or ()):
                    result.add(x)
                for x in (value.get('remove') or ()):
                    updated = True
                    result.discard(x)
                    remove(x)
            elif value is not None:
                result = set((value,))
            return result or set()

        # Allow targeted add/removals for ignoring/accepting. With this
        # order, accepts trump ignores (we may ignore a person and then
        # accept from them if they exist in both arrays).  We get our
        # incoming set (and remove specified drops) and then do any
        # new ignores or accepts.
        old_ignore = set(self.entities_ignoring_shared_data_from)
        ignoring = set_from_input('ignoring', old_ignore, 
                                  self.stop_ignoring_shared_data_from)
        ignoring_diff = ignoring - old_ignore
        handle_ext(self.reset_shared_data_from,
                   self.ignore_shared_data_from,
                   ignoring_diff)

        old_accept = set(self.entities_accepting_shared_data_from)
        accepting = set_from_input('accepting', old_accept, 
                                   self.stop_accepting_shared_data_from)
        accepting_diff = accepting - old_accept
        handle_ext(self.reset_shared_data_from,
                   self.accept_shared_data_from,
                   accepting_diff)
        return updated

    # ## Sharing

    def _get_dynamic_sharing_targets_for_read(self):
        """
        Overrides the super method to return both the communities we are a
        member of, plus the friends lists we ourselves have created that are dynamic.
        """
        result = set(super(User, self)._get_dynamic_sharing_targets_for_read())
        for fl in self.friendsLists.values():
            if IDynamicSharingTarget.providedBy(fl):
                result.add(fl)
        return result

    def _get_entities_followed_for_read(self):
        return set(super(User, self)._get_entities_followed_for_read())

    @Lazy
    def _circled_events_storage(self):
        """
        Right now, normally change events are not owned by anyone,
        they are simply referenced from the stream cache based on the
        intid of the *changed* object. Events are not sent for change
        events otherwise and thus they do not get their own intid.

        We want to keep a history of circled events however and we want
        to index them. If we just send the events to do this, we wind
        up with \"orphan\" change events in the index and intid utilities
        (because they are not owned by anyone, when the user gets cleaned up,
        we wouldn't know to clean the events up).

        The solution is to store them here and return them as sublocations so that
        they do get cleaned up. We don't expect there to be many, so we
        use a simple list.
        """
        self._p_changed = True
        result = PersistentList()
        result.__parent__ = self
        return result

    @property
    def circled_events(self):
        if "_circled_events_storage" in self.__dict__:
            return self._circled_events_storage
        return ()

    def accept_shared_data_from(self, source):
        """ 
        Accepts if not ignored; auto-follows as well.
        :return: A truth value. If this was the initial add, it will be the Change.
                If the source is ignored, it will be False.
        """

        if self.is_ignoring_shared_data_from(source):
            return False
        already_accepting = super(User, self).is_accepting_shared_data_from(source)
        if super(User, self).accept_shared_data_from(source):
            if already_accepting:
                # No change
                return True

            # Broadcast a change for the first time we're circled by this person
            # TODO: Do we need to implement a limbo state, pending acceptance
            # by the person?
            change = Change(Change.CIRCLED, source)
            change.creator = source
            # Not anchored, show at root and below. This overrides
            # the containerId gained from the source.
            change.containerId = ''
            # Also override the parent attribute copied from the source
            # to be us so we can treat this object like one of our sublocations
            change.__parent__ = self
            assert change.__name__ == source.username
            change.useSummaryExternalObject = True  # Don't send the whole user

            # Now that it's all configured, store it, give it an intid, and let
            # it get indexed. Let listeners do things do it (e.g., notabledata).
            # We still keep ownership though (its parent is set to us)...
            # it's important to do this before going through _noticeChange, which will
            # further disseminate this event
            self._circled_events_storage.append(change)
            lifecycleevent.created(change)
            lifecycleevent.added(change)

            # Bypass the whole mess of broadcasting and going through the DS and change listeners,
            # and just notice the incoming change.
            # TODO: Clean this up, go back to event based.
            self._noticeChange(change)

            return change  # which is both True and useful

    def is_accepting_shared_data_from(self, source):
        """ 
        We say we're accepting so long as we're not ignoring. 
        """
        # TODO: the 'incoming' group discussed in super will obsolete this
        return not self.is_ignoring_shared_data_from(source)

    def getFriendsList(self, name):
        """ 
        Returns the friends list having the given name, otherwise
        returns None. 
        """
        return self.friendsLists.get(name)

    def getFriendsLists(self, unused_name=None):
        """ 
        Returns all the friends lists
        """
        return tuple(self.friendsLists.values())

    def maybeCreateContainedObjectWithType(self, datatype, externalValue):
        if datatype in (self.devices.container_name, Device.mimeType):
            result = Device(externalValue)
        else:
            # FIXME: This is a hack to translate mimetypes to the old
            # style of name that works with self.containers
            if datatype in (FriendsList.mimeType, DynamicFriendsList.mimeType):
                datatype = self.friendsLists.container_name
            result = self.containers.maybeCreateContainedObjectWithType(datatype, externalValue)
        return result

    def addContainedObject(self, contained):
        # Must make sure it has a connection so it can generate
        # a OID/ID. We must use our connection, rather than
        # our storage's connection because if we were created
        # in the current transaction, our storage will not
        # have a connection (and adding the connection in
        # addition to the user in User.create_user fails later
        # on with spurious POSKeyError).
        # TODO: This should not be needed anymore as
        # intid listeners, etc, adapt to IKeyReference which adapts to IConnection
        # which walks the containment tree
        if      getattr(contained, '_p_jar', self) is None \
            and getattr(self, '_p_jar') is not None:
            self._p_jar.add(contained)

        result = self.containers.addContainedObject(contained)
        return result

    def deleteContainedObject(self, containerId, containedId):
        try:
            self.containers._p_activate()
            self.containers._p_jar.readCurrent(self.containers)
        except AttributeError:
            pass
        return self.containers.deleteContainedObject(containerId, containedId)

    # TODO: Could/Should we use proxy objects to automate
    # the update process? Allowing updates directly to deep objects?
    # What about monitoring the resources associated with the transaction
    # and if any of them belong to us posting a notification? (That seems
    # convenient but a poor separation of concerns)

    def getContainedObject(self, containerId, containedId, defaultValue=None):
        if containerId == self.containerId:  # "Users"
            return self
        return self.containers.getContainedObject(containerId, containedId, defaultValue)

    def getContainer(self, containerId, defaultValue=None, context_cache=None):
        __traceback_info__= containerId, context_cache
        stored_value = self.containers.getContainer(containerId, defaultValue)
        return stored_value

    def deleteContainer(self, containerId, remove_contained=True):
        if remove_contained:
            containers = self.containers.getContainer(containerId)
            containers.clear()
        self.containers.deleteContainer(containerId)

    def getAllContainers(self):
        """ 
        Returns all containers, as a map from containerId to container.
        The returned value *MUST NOT* be modified.
        """
        return self.containers.containers

    def values(self, of_type=None):
        """
        Returns something that iterates across all contained (owned) objects of this user.
        This is intended for use during migrations (enabling :func:`zope.generations.utility.findObjectsProviding`)
        and not general use.

        :param type of_type: If given, then only values that are instances of the given type
                will be returned.
        :type of_type: A class or interface.
        """
        # We could simply return getAllContainers().values() and let findObjectsProviding
        # deal with the traversal, but this way is a tad more general
        if interface.interfaces.IInterface.providedBy(of_type):
            test = of_type.providedBy
        elif isinstance(of_type, six.class_types):
            def test(x): return isinstance(x, of_type)
        else:
            def test(_): return True

        for container in self.getAllContainers().values():
            if not hasattr(container, 'values'):
                continue
            for o in container.values():
                if test(o):
                    yield o

        # TODO: This should probably be returning the annotations, too, just like
        # sublocations does, yes?

    def sublocations(self):
        """
        The sublocations of a user are his FriendsLists, his Devices,
        all the contained things he has created, and anything annotated
        on him that was in ILocation (see :mod:`zope.annotation.factory`).

        .. todo:: See comments in this method; annotations no longer supported.

        Note that this is used during the processing of :class:`zope.lifecycleevent.IObjectMovedEvent`,
        when :func:`zope.container.contained.dispatchToSublocations` comes through
        and recursively lets all the children know about the event. Also note that :class:`zope.lifecycleevent.IObjectRemovedEvent`
        is a kind of `IObjectMovedEvent`, so when the user is deleted, events are fired for all
        of his contained objects as well, allowing things like intid cleanup to work.
        """

        yield self.containers
        # Now anything else in containers that we put there that is actually
        # a child of us (this includes self.friendsLists and self.devices)
        for v in self.containers.itervalues():
            if getattr(v, '__parent__', None) is self:
                yield v

        # Now our circled events, these need to get deleted/indexed etc
        for change in self._circled_events_storage:
            yield change

        # If we have annotations, then if the annotated value thinks of
        # us as a parent, we need to return that. See zope.annotation.factory
        # XXX FIXME:
        # This is wrong (and so commented out). Specifically, for ObjectAddedEvent,
        # any annotations we have already established get their own intids,
        # even if they are not meant to be addressable like that, potentially
        # keeping them alive for too long. This also means that annotations get
        # indexed, which is probably also not what we want. It causes issues for
        # IUserProfile annotation in particular.
        # TODO: But what does turning this off break? Certain migration patterns?
        # Or does it break deleting a user? Chat message storage winds up with
        # too many objects still with intids?
        # annotations = zope.annotation.interfaces.IAnnotations(self, {})

        # Technically, IAnnotations doesn't have to be iterable of values,
        # but it always is (see zope.annotation.attribute)
        # for val in annotations.values():
        #     if getattr( val, '__parent__', None ) is self:
        #         yield val

    def _is_container_ntiid(self, containerId):
        """
        Filters out things that are not used as NTIIDs. In the future,
        this will be easy (as soon as everything is tag-based). Until then,
        we rely on the fact that all our custom keys are upper cased.
        """
        return  len(containerId) > 1 \
            and (containerId.startswith('tag:nextthought.com') or containerId[0].islower())

    def iterntiids(self, include_stream=True, stream_only=False):
        """
        Returns an iterable across the NTIIDs that are relevant to this user.
        """
        # Takes into account our things, things shared directly to us,
        # and things found in dynamic things we care about, which includes
        # our memberships and things we own
        seen = set()
        if not stream_only:
            for k in self.containers:
                if self._is_container_ntiid(k) and k not in seen:
                    seen.add(k)
                    yield k

            for k in self.containersOfShared:
                if self._is_container_ntiid(k) and k not in seen:
                    seen.add(k)
                    yield k
        if include_stream:
            for k in self.streamCache:
                if self._is_container_ntiid(k) and k not in seen:
                    seen.add(k)
                    yield k

        fl_set = {
            x for x in self.friendsLists.values() if IDynamicSharingTarget.providedBy(x)
        }
        interesting_dynamic_things = set(self.dynamic_memberships) | fl_set
        for com in interesting_dynamic_things:
            if not stream_only and hasattr(com, 'containersOfShared'):
                for k in com.containersOfShared:
                    if self._is_container_ntiid(k) and k not in seen:
                        seen.add(k)
                        yield k
            if include_stream and hasattr(com, 'streamCache'):
                for k in com.streamCache:
                    if self._is_container_ntiid(k) and k not in seen:
                        seen.add(k)
                        yield k

    def iter_containers(self):
        # TODO: Not sure about this. Who should be responsible for
        # the UGD containers? Should we have some different layout
        # for that (probably).
        return (v
                for v in self.containers.containers.itervalues()
                if INamedContainer.providedBy(v))
    itercontainers = iter_containers

    def iter_objects(self, include_stream=True, stream_only=False,
                     include_shared=False, only_ntiid_containers=False):

        def _loop(container, unwrap=False):
            if hasattr(container, 'values'):
                collection = container.values()
            else:
                collection = container
            for obj in collection:
                obj = self.containers._v_unwrap(obj) if unwrap else obj
                if isBroken(obj):
                    logger.error("ignoring broken object %s", type(obj))
                else:
                    yield obj

        if not stream_only:
            for name, container in self.containers.iteritems():
                if not only_ntiid_containers or self._is_container_ntiid(name):
                    for obj in _loop(container, True):
                        yield obj

        if include_stream:
            for name, container in self.streamCache.iteritems():
                if not only_ntiid_containers or self._is_container_ntiid(name):
                    for obj in _loop(container, False):
                        yield obj

        if include_shared:
            fl_set = {
                x for x in self.friendsLists.values() if IDynamicSharingTarget.providedBy(x)
            }

            interesting_dynamic_things = set(self.dynamic_memberships) | fl_set
            for com in interesting_dynamic_things:
                if not stream_only and hasattr(com, 'containersOfShared'):
                    for name, container in com.containersOfShared.items():
                        if not only_ntiid_containers or self._is_container_ntiid(name):
                            for obj in _loop(container, False):
                                yield obj

                if include_stream and hasattr(com, 'streamCache'):
                    for name, container in com.streamCache.iteritems():
                        if not only_ntiid_containers or self._is_container_ntiid(name):
                            for obj in _loop(container, False):
                                yield obj

    def iter_intids(self, include_stream=True, stream_only=False,
                    include_shared=False, only_ntiid_containers=False):
        seen = set()
        intid = component.getUtility(IIntIds)
        for obj in self.iter_objects(include_stream=include_stream,
                                     stream_only=stream_only,
                                     include_shared=include_shared,
                                     only_ntiid_containers=only_ntiid_containers):

            uid = intid.queryId(obj)
            if uid is not None and uid not in seen:
                seen.add(uid)
                yield uid

    def updates(self):
        """
        This is officially deprecated now.

        noisy if enabled; logic in flagging_views still needs its existence until rewritten
        """
        return _NOOPCM

    def _acceptIncomingChange(self, change, direct=True):
        accepted = super(User, self)._acceptIncomingChange(change, direct=direct)
        if accepted:
            self.notificationCount.increment()
            self._broadcastIncomingChange(change)

    def _broadcastIncomingChange(self, change):
        """
        Distribute the incoming change to any connected devices/sessions.
        This is an extension point for layers.
        """
        # TODO: Move this out to a listener somewhere
        apnsCon = component.queryUtility(INotificationService)
        # NOTE: At this time, no such component is actually
        # being registered.
        if not apnsCon:
            if self.devices:
                logger.warn("No APNS connection, not broadcasting change")
            return
        if self.devices:
            from nti.apns.payload import APNSPayload
            # If we have any devices, notify them
            userInfo = None
            if change.containerId:
                # Valid NTIIDs are also valid URLs; this
                # condition is mostly for legacy code (tests)
                if ntiids.is_valid_ntiid_string(change.containerId):
                    userInfo = {'url:': change.containerId}

            payload = APNSPayload(badge=self.notificationCount.value,
                                  sound='default',
                                  # TODO: I18N text for this
                                  # change.creator.preferredDisplayName + ' shared an object',
                                  alert='An object was shared with you',
                                  userInfo=userInfo)
            for device in self.devices.itervalues():
                if not isinstance(device, Device):
                    continue
                __traceback_info__ = device, payload, change
                try:
                    apnsCon.sendNotification(device.deviceId, payload)
                except Exception:  # Big catch: this is not crucial, we shouldn't hurt anything without it
                    logger.exception("Failed to send APNS notification")

    def _xxx_extra_intids_of_memberships(self):
        # We want things shared with the DFLs we own to be counted
        # as visible to us
        for x in self.friendsLists.values():
            if IDynamicSharingTargetFriendsList.providedBy(x):
                # Direct access is a perf optimization, this is called a lot
                yield x._ds_intid

# We have a few subclasses of User that store some specific
# information and directly implement some interfaces.
# Right now, we're not exposing this information directly to clients,
# so this is an implementation detail. Thus we make their class names
# be 'User' as well.
# TODO: MimeTypes?


@interface.implementer(IOpenIdUser)
class OpenIdUser(User):

    __external_class_name__ = 'User'

    identity_url = None

    def __init__(self, username, **kwargs):
        id_url = kwargs.pop('identity_url', None)
        super(OpenIdUser, self).__init__(username, **kwargs)
        if id_url:
            self.identity_url = id_url


@interface.implementer(IFacebookUser)
class FacebookUser(User):

    __external_class_name__ = 'User'
 
    facebook_url = None

    def __init__(self, username, **kwargs):
        id_url = kwargs.pop('facebook_url', None)
        super(FacebookUser, self).__init__(username, **kwargs)
        if id_url:
            self.facebook_url = id_url


@component.adapter(IDeviceFeedbackEvent)
def user_devicefeedback(msg):
    def feedback():
        deviceId = msg.deviceId
        hexDeviceId = deviceId.encode('hex')
        # TODO: Very inefficient
        # Switch this to ZCatalog/repoze.catalog
        if msg.timestamp < 0:
            return
        datasvr = get_shared_dataserver()
        logger.debug('Searching for device %s', hexDeviceId)
        for user in (u for u in datasvr.root['users'].itervalues() if isinstance(u, User)):
            if hexDeviceId in user.devices:
                logger.debug('Found device id %s in user %s',
                             hexDeviceId, user)
                del user.devices[hexDeviceId]

    # Be sure we run in the right site and transaction.
    # Our usual caller is in nti.apns and knows nothing about that.
    # NOTE: We are not using a site policy here so the listener is limited
    if IConnection(component.getSiteManager(), None):
        feedback()
    else:
        component.getUtility(IDataserverTransactionRunner)(feedback)


@component.adapter(ITargetedStreamChangeEvent)
def onChange(event):
    entity = event.entity
    msg = event.object
    if hasattr(entity, '_noticeChange'):
        try:
            entity._p_activate()
            entity._p_jar.readCurrent(entity)
        except AttributeError:
            pass
        entity._noticeChange(msg)


zope.deferredimport.deprecatedFrom(
    "Moved to nti.dataserver.users.black_list",
    "nti.dataserver.users.black_list",
    "UserBlacklistedStorage")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.dataserver.users.digest",
    "nti.dataserver.users.digest",
    "_UserDigestEmailMetadata")
