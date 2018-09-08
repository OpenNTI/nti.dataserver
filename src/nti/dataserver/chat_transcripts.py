#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Transcripts for chats as stored on users.

The object model
================

The concept of a meeting room is something that can contain resources.
Meeting rooms hold meetings (at most one meeting at a time). The
meetings are transcripted and this transcript is attached as a
resource to the room. A meeting's ContainerID is the ID of the room.
Within a meeting, a MessageInfo's ContainerID is the ID of the
meeting. Some meetings take place "in the hallway" or "around the
cooler" and as such belong to no room. When they finish, the
transcript is accessible just to the users that participated. (These
meetings may still have ContainerIDs of other content, and they will
be accessible from that location, as is anything contained there.)


Garbage Collection
===================

.. note:: Much of the following information should be considered outdated, as
   messages are now stored on the user, and always use intids.
   See :mod:`nti.dataserver.meeting_storage`

Currently, users are stored in a different database than Meeting and
MessageInfo objects (which are together with sessions). If that
database is packed and GC'd without using zc.zodbgc to do a multi-GC,
then we can lose all our transcripts. It's not as simple as just
moving those objects to the User database, either, because we may be
sharded. The approach to solving the problem, then, is to keep
/explicit/ weak refs and use them as long as possible (TODO: Does that
still break with zc.zodbgc?), but also make a copy in our database to
fallback on (in some cases, the objects are mutated after being
transcripted so the copy may not be perfectly in sync or we'd always
just use it). Note that this must be a deep copy: these are persistent
objects with sub-objects stored in the same initial database, and a
shallow copy would fail after GC for the same reasons as the original
object. Consequently, we use zope.copy for its deep-copy approach (via
pickling) in addition to its hooks support.

This is unfortunately quite a bit more expensive than strictly necessary:

* Profiling shows that the reference and the copy **double** the
  amount of time spent storing transcripts. Most of that time is in
  the copy itself
* Using a KeyReferenceToPersistent as the messages key amounts to a
  third of the cost.
* Using int ids for the messages an 64-bit IOBTree shaves 20% or so of
  the cost relative to an OOBTree and the string UUID of the message
* In a 12-second, 5000 msg, 4 user test (without copy), half the time
  is in committing, and one third is spent in serializing so
  simplifying the MessageInfo objects might be worth it, but there's
  not much to simplify.
* As of 2012-07-26, that same 5000 msg, 4-user test, through the use
  of pervasive intids, and sharing datastructure changes, is down to
  5.5 seconds instead of 12.
* Making MessageInfo non-Persistent substantially increases the
  runtime (back to copy levels, because it does amount to making
  copies)

In light of this info, given that transcript storage is a performance
sensitive operation, and that (a) we know how to run GCs cross
database without losing refs either using zc.zodbcgc or simply having
the storage keep all non-historical objects, and that RelStorage
reduces the need to run GC anyway, we opt to reverse the previous
policy and simply store a weak ref.

Experiments with using intids and an IISet in MeetingTranscriptStorage
were a wash, as were using an OOTreeSet instead of an OOBTree. The
biggest win is simply reducing all the transactions to one. There's
probably a big win in unifying the indexes. Try an KeywordIndex.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time

from persistent import Persistent

from repoze.lru import lru_cache

import six

from ZODB.POSException import POSError

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import Lazy
from zope.cachedescriptors.property import CachedProperty

from zope.intid.interfaces import IIntIds

from nti.chatserver.interfaces import IMeeting
from nti.chatserver.interfaces import IMessageInfo
from nti.chatserver.interfaces import IUserTranscriptStorage
from nti.chatserver.interfaces import IMessageInfoPostedToRoomEvent

from nti.coremetadata.mixins import ZContainedMixin

from nti.dataserver.activitystream_change import Change

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ILinked
from nti.dataserver.interfaces import ICreated
from nti.dataserver.interfaces import ITranscript
from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import SYSTEM_USER_NAME
from nti.dataserver.interfaces import ITranscriptSummary

from nti.dataserver.users.users import User

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.links import links

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectIO
from nti.externalization.interfaces import LocatedExternalDict

from nti.mimetype.mimetype import ModeledContentTypeAwareRegistryMetaclass

from nti.ntiids import ntiids

from nti.property.property import read_alias

from nti.schema.eqhash import EqHash

from nti.schema.field import Object

from nti.wref.interfaces import IWeakRef

from nti.zope_catalog.interfaces import INoAutoIndexEver

logger = __import__('logging').getLogger(__name__)


# interfaces


class _IMeetingTranscriptStorage(ICreated,  # ICreated so they get an ACL
                                 INoAutoIndexEver):

    meeting = Object(IMeeting,
                     title=u"The meeting we hold messages to; may go null")

    def add_message(msg):
        """
        Store the message with this transcript.
        """

    def remove_message(msg):
        """
        Remove the message from this transcript.
        """

    def itervalues():
        """
        Iterate all the messages in this transcript.
        """


# implementations


@interface.implementer(_IMeetingTranscriptStorage)
class _AbstractMeetingTranscriptStorage(PersistentCreatedModDateTrackingObject,
                                        ZContainedMixin):

    """
    The storage for the transcript of a single session. Private object, not public.
    """

    creator = SYSTEM_USER_NAME

    def __init__(self, meeting):
        super(_AbstractMeetingTranscriptStorage, self).__init__()
        self._meeting_ref = IWeakRef(meeting)

    @property
    def meeting(self):
        return self._meeting_ref()

    def add_message(self, msg):
        """
        Stores the message in this transcript.
        """
        raise NotImplementedError()

    def remove_message_by_id(self, uid):
        """
        Removes the message from this transcript.
        """
        raise NotImplementedError()

    def remove_message(self, msg):
        """
        Removes the message from this transcript.
        """
        raise NotImplementedError()

    def __contains__(self, key):
        """
        Check if a message is in this transcript
        """
        raise NotImplementedError()

    def itervalues(self):
        raise NotImplementedError()

    # for finding MessageInfos with zope.genartions.findObjectsMatching
    # In some (early!) migration cases, it may be needed to disable this due to the
    # switch to callable refs: the iterator cannot iterate non-callable objects, and
    # that breaks generations.findObjectsMatching, # it doesn't catch that exception.
    # Instead, the migration code needs to modify this class dynamically.
    def values(self):
        return self.itervalues()

# The class _MeetingTranscriptStorage extended AbstractMeetingTranscriptStorage and
# stored messages in an OOBTree as WeakRefs keyed by message ID. With the move
# to user-based message storage, it should have gotten dropped and all instances left
# in the old Sessions DB. Old migration code that happens to encounter them
# will instead encounter these objects that are not iterable and will be ignored...
# they are just enough skeletons to enable them to be deleted from the user...
# this is temporary likewise for from nti.zodb.wref import CopyingWeakRef as
# _CopyingWeakRef # bwc for things in the database
@interface.implementer(_IMeetingTranscriptStorage)
class _MeetingTranscriptStorage(Persistent, ZContainedMixin):
    pass


@interface.implementer(_IMeetingTranscriptStorage)
class _DocidMeetingTranscriptStorage(_AbstractMeetingTranscriptStorage):
    """
    The storage for the transcript of a single session based on docids.
    Private object, not public.
    """

    def __init__(self, meeting):
        intids = self._intids
        # pylint: disable=no-member
        if intids.queryId(meeting) is None:
            # This really shouldn't be happening anywhere. Why is it?
            logger.warning(
                "Transcript for a meeting without an intid. %s",
                meeting)
            intids.register(meeting)
            lifecycleevent.modified(meeting)

        super(_DocidMeetingTranscriptStorage, self).__init__(meeting)
        self.messages = intids.family.II.TreeSet()

    def add_message(self, msg):
        """
        Stores the message in this transcript.
        """
        # pylint: disable=no-member
        self.messages.add(self._intids.getId(msg))

    def remove_message_by_id(self, uid):
        if uid is not None and uid in self.messages:
            self.messages.remove(uid)
            return True
        return False

    def remove_message(self, msg):
        """
        Removes the message from this transcript.
        """
        # pylint: disable=no-member
        uid = self._intids.queryId(msg)
        result = self.remove_message_by_id(uid)
        return result

    def itervalues(self):
        intids = self._intids
        for iid in self.messages:
            # pylint: disable=no-member
            msg = intids.queryObject(iid)
            if msg is not None:
                yield msg

    def __contains__(self, key):
        if not isinstance(key, six.integer_types):
            # pylint: disable=no-member
            key = self._intids.queryId(key)
        return key is not None and key in self.messages

    @CachedProperty
    def _intids(self):
        return component.getUtility(IIntIds)


@lru_cache(10000)
def _transcript_ntiid(meeting, creator_username=None, nttype=ntiids.TYPE_TRANSCRIPT_SUMMARY):
    """
    :return: A NTIID string representing the transcript (summary) for the
            given meeting (chat session) with the given participant.
    """
    return ntiids.make_ntiid(base=meeting.id,
                             provider=creator_username,
                             nttype=nttype)


def _get_by_oid(*unused_args, **unused_kwargs):
    return None
_get_by_oid.get_by_oid = _get_by_oid


def get_meeting_oid(ntiid):
    if not ntiids.is_ntiid_of_type(ntiid, ntiids.TYPE_OID):
        # We'll take any type, usually a TRANSCRIPT type
        ntiid = ntiids.make_ntiid(base=ntiid,
                                  provider=SYSTEM_USER_NAME,
                                  nttype=ntiids.TYPE_OID)
    return ntiid


@component.adapter(IUser)
@interface.implementer(IUserTranscriptStorage)
class _UserTranscriptStorageAdapter(object):
    """
    The storage for all of a user's transcripts.

    You can look up transcripts by meeting ID.

    """

    def __init__(self, user):
        self._user = user

    def transcript_for_meeting(self, object_id):
        result = None
        meeting_oid = get_meeting_oid(object_id)
        meeting = ntiids.find_object_with_ntiid(meeting_oid)
        if meeting is not None:
            storage_id = _transcript_ntiid(meeting, self._user.username)
            storage = self._user.getContainedObject(meeting.containerId,
                                                    storage_id)
            result = Transcript(storage) if storage else None
        else:
            # OK, the meeting has gone away, GC'd and no longer directly referencable.
            # Try to find the appropriate storage manually
            # TODO: finish converting this all to intids

            # We will accept either a match for the OID (unlikely at this point)
            # the original object_id (commonly a UUID during testing), or,
            # if we were given a TRANSCRIPT type, then we make a UUID (again,
            # for testing). We also accept a provider-mismatch for UUID values
            # (again, testing)
            acceptable_oids = (meeting_oid, object_id)
            specific = ntiids.get_specific(object_id)
            if ntiids.is_ntiid_of_type(object_id, ntiids.TYPE_TRANSCRIPT):
                acceptable_oids += (ntiids.make_ntiid(base=object_id,
                                                      nttype=ntiids.TYPE_UUID),)

            for value in self._user.values(of_type=_IMeetingTranscriptStorage):
                value_meeting_id = value.meeting.ID
                if      value_meeting_id in acceptable_oids \
                    or (    ntiids.is_ntiid_of_type(value_meeting_id, ntiids.TYPE_UUID)
                        and ntiids.get_specific(value_meeting_id) == specific):
                    result = Transcript(value)
                    break
        return result

    def _transcript_storages(self):
        for container in self._user.getAllContainers().values():
            if not hasattr(container, "values"):
                continue
            for storage in container.values():
                if _IMeetingTranscriptStorage.providedBy(storage):
                    yield storage

    @property
    def meetings(self):
        result = []
        for storage in self._transcript_storages():
            result.append(storage.meeting)
        return result

    @property
    def transcripts(self):
        result = []
        for storage in self._transcript_storages():
            result.append(Transcript(storage))
        return result

    @property
    def transcript_summaries(self):
        result = []
        for storage in self._transcript_storages():
            result.append(TranscriptSummaryAdapter(storage))
        return result

    def add_message(self, meeting, msg):
        if not meeting.containerId:
            logger.warning(
                "Meeting (room) has no container id, will not transcript %s",
                 meeting)
            # Because we won't be able to store the room on the user.
            # This is actually a bug in creating the room.
            return False

        # Our transcript storage we store with the
        # provider ID of our user
        storage_id = _transcript_ntiid(meeting, self._user.username)
        storage = self._user.getContainedObject(meeting.containerId, 
                                                storage_id)
        if storage is None:
            storage = _DocidMeetingTranscriptStorage(meeting)
            storage.id = storage_id
            storage.containerId = meeting.containerId
            storage.creator = self._user
            self._user.addContainedObject(storage)
        storage.add_message(msg)
        return storage

    def remove_message(self, meeting, msg):
        if not meeting.containerId:
            logger.warning("Meeting (room) has no container id", meeting)
            return False
        storage_id = _transcript_ntiid(meeting, self._user.username)
        storage = self._user.getContainedObject(meeting.containerId,
                                                storage_id)
        if storage is not None:
            storage.remove_message(msg)
        return storage


@interface.implementer(IUserTranscriptStorage)
class _MissingStorage(object):
    """
    A storage that's always empty and blank.
    """

    def transcript_for_meeting(self, unused_meeting_id):
        return None  # pragma: no cover

    @property
    def transcripts(self):
        return ()  # pragma: no cover

    @property
    def transcript_summaries(self):
        return ()  # pragma: no cover

    def add_message(self, meeting, msg):
        pass

    def remove_message(self, msg):
        pass
_BLANK_STORAGE = _MissingStorage()


def _ts_storage_for(owner):
    user = User.get_user(owner)
    storage = component.queryAdapter(user, IUserTranscriptStorage,
                                     default=_BLANK_STORAGE)
    return storage


@component.adapter(IMessageInfo, IMessageInfoPostedToRoomEvent)
def _save_message_to_transcripts_subscriber(msg_info, event):
    """
    Event handler that saves messages to the appropriate transcripts.
    """
    meeting = event.room

    change = Change(Change.CREATED, msg_info)
    change.creator = msg_info.Sender

    for owner in set(event.recipients):
        # pylint: disable=unused-variable
        __traceback_info__ = owner, meeting
        storage = _ts_storage_for(owner)
        storage.add_message(meeting, msg_info)


def transcript_for_user_in_room(username, room_id):
    """
    Returns a :class:`Transcript` for the user in room.
    If the user wasn't in the room, returns None.
    """
    storage = _ts_storage_for(username)
    return storage.transcript_for_meeting(room_id)


def transcript_summaries_for_user_in_container(username, containerId):
    """
    Primarily intended for debugging

    :return: Map of room/transcript id to :class:`TranscriptSummary` objects for the user that
            have taken place in the given containerId. The map will have attributes `lastModified`
            and `creator`.

    """
    storage = _ts_storage_for(username)
    data = LocatedExternalDict()
    last_modified = 0
    for summary in storage.transcript_summaries:
        if summary.RoomInfo.containerId == containerId:
            data[summary.RoomInfo.ID] = summary
            last_modified = max(last_modified, summary.LastModified)
    data.lastModified = last_modified
    data.creator = username
    return data


def list_transcripts_for_user(username):
    """
    Returns an Iterable of :class:`TranscriptSummary` objects for the user.
    """
    storage = _ts_storage_for(username)
    return storage.transcript_summaries


@interface.implementer(ITranscriptSummary)
@component.adapter(_IMeetingTranscriptStorage)
def TranscriptSummaryAdapter(meeting_storage):
    """
    Registered as a ZCA adapter factory to get a :class:`nti_interfaces.ITranscriptSummary`.

    Deals gracefully with bad meeting storage objects that are missing components
    such as a room due to GC.
    """
    try:
        if meeting_storage is not None and meeting_storage.meeting is not None:
            return TranscriptSummary(meeting_storage)
    except (POSError, AssertionError):  # pragma: no cover
        logger.exception("Meeting object gone missing.")
        return None


@interface.implementer(IInternalObjectIO)
@component.adapter(_IMeetingTranscriptStorage)
def _MeetingTranscriptStorageExternalObjectAdapter(meeting_storage):
    summary = ITranscriptSummary(meeting_storage)
    return IInternalObjectIO(summary)


@EqHash('id')
@six.add_metaclass(ModeledContentTypeAwareRegistryMetaclass)
@interface.implementer(IZContained,
                       ILinked,
                       ITranscriptSummary)
@component.adapter(_IMeetingTranscriptStorage)
class TranscriptSummary(object):
    """
    The transcript summary for a user in a room.
    """

    __parent__ = None
    __name__ = None
    id = read_alias('__name__')

    links = ()
    _NTIID_TYPE_ = ntiids.TYPE_TRANSCRIPT_SUMMARY

    # BWC aliases
    NTIID = read_alias('__name__')
    ContainerId = read_alias('containerId')
    LastModified = read_alias('lastModified')

    def __init__(self, meeting_storage):
        """
        :param _IMeetingTranscriptStorage meeting_storage: The storage for the user in the room.
        """
        super(TranscriptSummary, self).__init__()
        room = meeting_storage.meeting
        assert room
        assert room.ID
        self.creator = meeting_storage.creator
        self.RoomInfo = room
        self.containerId = room.ID
        self.__parent__ = room
        self.__name__ = _transcript_ntiid(room, self.creator.username, self._NTIID_TYPE_)

        # TODO: What should the LastModified be? The room doesn't
        # currently track it. We're using the max for our messages, which may
        # not be right?
        created_time = time.time()
        last_modified = 0.0
        contributors = set()
        for message in meeting_storage.itervalues():
            last_modified = max(last_modified, getattr(message, 'LastModified', 0.0))
            created_time = min(created_time, getattr(message, 'createdTime', created_time))
            contributors.update(getattr(message, 'sharedWith', ()) or ())

        self.lastModified = last_modified
        self.createdTime = created_time
        self.Contributors = contributors

        self.links = self._create_links(meeting_storage)

    def _create_links(self, meeting_storage):
        # TODO: constant
        return (links.Link(Transcript(meeting_storage), rel="transcript"),)

    def __reduce__(self):
        """
        These objects cannot be pickled.
        """  # because they hold other persistent objects that are meant to be weak-refd
        raise TypeError()


@component.adapter(ITranscriptSummary)
class TranscriptSummaryInternalObjectIO(InterfaceObjectIO):
    _ext_iface_upper_bound = ITranscriptSummary


# For purposes of filtering during UGD queries, make the objects that
# store messages (and which are in the users containers) appear to be
# transcript summaries, since that is what they will externalize as.
# TODO: This design is wonky
# pylint: disable=no-member
_AbstractMeetingTranscriptStorage.mimeType = TranscriptSummary.mimeType


@six.add_metaclass(ModeledContentTypeAwareRegistryMetaclass)
@interface.implementer(ITranscript)
@component.adapter(_IMeetingTranscriptStorage)
class Transcript(TranscriptSummary):
    """
    The transcript for a user in a room.
    """

    _NTIID_TYPE_ = ntiids.TYPE_TRANSCRIPT

    def __init__(self, meeting_storage):
        """
        :param _MeetingTranscriptStorage meeting_storage: The storage for the user in the room.
        """
        super(Transcript, self).__init__(meeting_storage)
        self._meeting_storage = meeting_storage

    @Lazy
    def Messages(self):
        return list(self._meeting_storage.itervalues())

    def _create_links(self, unused_meeting_storage):
        return ()

    def __len__(self):
        return len(self.Messages)

    def __nonzero__(self):
        return True

    def __getitem__(self, msg_id):
        return self.get_message(msg_id)

    def get_message(self, msg_id):
        """
        :return: The message in the transcript with the given ID, or None.
        """
        # pylint: disable=not-an-iterable
        for m in self.Messages:
            if m.ID == msg_id:
                return m


def _get_meeting_id(msg):
    ntiid = msg.containerId
    return get_meeting_oid(ntiid) if ntiid else ntiid


def _get_creator(msg):
    result = msg.creator
    if not IUser.providedBy(result):
        result = User.get_user(result or '')
    return result


@component.adapter(IMessageInfo)
@interface.implementer(IMeeting)
def _message_info_to_meeting(msg):
    ntiid = _get_meeting_id(msg)
    return ntiids.find_object_with_ntiid(ntiid) if ntiid else None


@component.adapter(IMessageInfo, IUser)
@interface.implementer(_IMeetingTranscriptStorage)
def _message_info_to_transcript_storage(msg, user):
    meeting = IMeeting(msg, None)
    if IMeeting.providedBy(meeting):
        storage_id = _transcript_ntiid(meeting, user.username)
        storage = user.getContainedObject(meeting.containerId,
                                          storage_id)
        return storage


@component.adapter(IMessageInfo, IUser)
@interface.implementer(ITranscriptSummary)
def _message_info_to_transcript_summary(msg, user):
    storage = component.queryMultiAdapter((msg, user), 
                                          _IMeetingTranscriptStorage)
    return ITranscriptSummary(storage, None)


@interface.implementer(ITranscript)
@component.adapter(IMessageInfo, IUser)
def _message_info_to_transcript(msg, user):
    ntiid = _get_meeting_id(msg)
    return transcript_for_user_in_room(user.username, ntiid)
