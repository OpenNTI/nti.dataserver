#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time
import uuid
import datetime

from persistent import Persistent

from persistent.list import PersistentList

import six

from zope import component
from zope import interface

from zope.deprecation import deprecate

from zope.dublincore.interfaces import IDCTimes

from nti.base._compat import text_

from nti.chatserver.interfaces import STATUS_INITIAL
from nti.chatserver.interfaces import CHANNEL_DEFAULT

from nti.chatserver.interfaces import IMessageInfo

from nti.coremetadata.schema import MessageInfoBodyFieldProperty

from nti.dataserver.contenttypes.base import _make_getitem

from nti.dataserver.sharing import AbstractReadableSharedMixin

from nti.dataserver.users.entity import Entity

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.externalization import to_external_object

from nti.externalization.interfaces import IClassObjectFactory

from nti.externalization.internalization import update_from_external_object

from nti.externalization.proxy import removeAllProxies

from nti.mimetype.mimetype import ModeledContentTypeAwareRegistryMetaclass

from nti.property.property import alias
from nti.property.property import read_alias

from nti.threadable.externalization import ThreadableExternalizableMixin

from nti.threadable.threadable import Threadable as ThreadableMixin

logger = __import__('logging').getLogger(__name__)

# Warning!!! MessageInfo is a mess. Unify better with IContent
# and the other content types.
# We manually re-implement IDCTimes (should extend
# CreatedModDateTrackingObject)


@six.add_metaclass(ModeledContentTypeAwareRegistryMetaclass)
@interface.implementer(IMessageInfo, IDCTimes)
class MessageInfo(AbstractReadableSharedMixin,
                  ThreadableMixin,
                  Persistent):

    __parent__ = None
    __name__ = alias('ID')

    __external_can_create__ = True

    _prefer_oid_ = False

    # The usernames of occupants of the initial room, and others
    # the transcript should go to. Set by policy.
    sharedWith = ()
    channel = CHANNEL_DEFAULT
    body = MessageInfoBodyFieldProperty(IMessageInfo['body'])

    recipients = ()

    containerId = None
    Creator = None  # aka Sender. Forcibly set by the handler

    def __init__(self):
        super(MessageInfo, self).__init__()
        self.sharedWith = set()
        self.Status = STATUS_INITIAL
        self.LastModified = time.time()
        self.ID = text_(uuid.uuid4().hex)
        self.CreatedTime = self.LastModified
        self._v_sender_sid = None  # volatile. The session id of the sender.

    Sender = alias('Creator')
    creator = alias('Creator')

    # From AbstractReadableSharedMixin
    @property
    def sharingTargets(self):
        result = set()
        for x in self.sharedWith:
            x = Entity.get_entity(x)
            if x is not None:
                result.add(x)
        return result

    # From IWritableSharable
    def clearSharingTargets(self):
        self.sharedWith = MessageInfo.sharedWith

    # We don't really do sharing with entities, just usernames. So the entity-based
    # methods are not implemented
    def addSharingTarget(self, target):
        raise NotImplementedError()

    def updateSharingTargets(self, replacements):
        raise NotImplementedError()

    def setSharedWithUsernames(self, usernames):
        self.sharedWith = usernames

    id = read_alias('ID')
    MessageId = read_alias('ID')  # bwc

    createdTime = alias('CreatedTime')
    lastModified = alias('LastModified')

    Timestamp = alias('LastModified')  # bwc

    # IDCTimes
    created = property(lambda self: datetime.datetime.fromtimestamp(self.createdTime),
                       lambda self, dt: setattr(self, 'createdTime', time.mktime(dt.timetuple())))

    modified = property(lambda self: datetime.datetime.fromtimestamp(self.lastModified),
                        lambda self, dt: self.updateLastModIfGreater(time.mktime(dt.timetuple())))

    def updateLastModIfGreater(self, t):  # copied from ModDateTrackingObject
        """
        Only if the given time is (not None and) greater than this object's is this object's time changed.
        """
        if t is not None and t > self.lastModified:
            self.lastModified = t
        return self.lastModified

    def updateLastMod(self):
        pass

    def get_sender_sid(self):
        """
        When this message first arrives, this will
        be the session id of the session that sent
        the message. After that, it will be None.
        """
        return getattr(self, '_v_sender_sid', None)

    def set_sender_sid(self, sid):
        setattr(self, '_v_sender_sid', sid)

    sender_sid = property(get_sender_sid, set_sender_sid)

    @property
    def rooms(self):
        return [self.containerId]

    Body = alias('body')

    @property
    def recipients_without_sender(self):
        """
        All the recipients of this message, excluding the Sender.
        """
        recip = set(self.recipients)
        recip.discard(self.Sender)
        return recip

    @property
    def recipients_with_sender(self):
        """
        All the recipients of this message, including the Sender.
        """
        recip = set(self.recipients)
        recip.add(self.Sender)
        return recip

    def is_default_channel(self):
        return self.channel is None or self.channel == CHANNEL_DEFAULT

    __getitem__ = _make_getitem('body')

    __ext_ignore_toExternalObject__ = True

    @deprecate("Prefer to use nti.externalization directly.")
    def toExternalObject(self):
        return to_external_object(self)

    __ext_ignore_updateFromExternalObject__ = True

    @deprecate("Prefer to use nti.externalization directly.")
    def updateFromExternalObject(self, ext_object, context=None):
        return update_from_external_object(self, ext_object, context=context)


@component.adapter(IMessageInfo)
class MessageInfoInternalObjectIO(ThreadableExternalizableMixin,
                                  InterfaceObjectIO):

    _ext_iface_upper_bound = IMessageInfo

    # NOTE: inReplyTo and 'references' do not really belong here
    _excluded_out_ivars_ = InterfaceObjectIO._excluded_out_ivars_ | frozenset({
        'MessageId', 'flattenedSharingTargetNames', 'flattenedSharingTargets',
        'sharingTargets', 'inReplyTo', 'references'
    })

    def __init__(self, context):
        super(MessageInfoInternalObjectIO, self).__init__(context)

    context = alias('_ext_self')

    _excluded_in_ivars_ = {
        'MessageId', 'sharedWith'
    } | InterfaceObjectIO._excluded_in_ivars_

    _prefer_oid_ = False
    _update_accepts_type_attrs = True

    def _ext_replacement(self):
        return removeAllProxies(self.context)

    def toExternalObject(self, mergeFrom=None, **kwargs):
        result = super(MessageInfoInternalObjectIO, self).toExternalObject(mergeFrom=mergeFrom, **kwargs)
        msg = self.context
        if msg.body is not None:
            # alias for old code.
            result['Body'] = result['body']
        assert 'channel' in result
        assert 'recipients' in result
        return result

    def updateFromExternalObject(self, parsed, *args, **kwargs):  # pylint: disable=arguments-differ
        if 'Body' in parsed and 'body' not in parsed:
            parsed['body'] = parsed['Body']
        super(MessageInfoInternalObjectIO, self).updateFromExternalObject(parsed, *args, **kwargs)
        msg = self.context
        # make recipients be stored as a persistent list.
        # In theory, this helps when we have to serialize the message object
        # into the database multiple times, by avoiding extra copies (like when we transcript)
        # This also results in us copying incoming recipients
        if msg.recipients and 'recipients' in parsed:
            msg.recipients = PersistentList(msg.recipients)


@interface.implementer(IClassObjectFactory)
class MessageInfoFactory(object):

    description = title = "MessageInfo factory"

    def __init__(self, *args):
        pass

    def __call__(self, *unused_args, **unused_kw):
        return MessageInfo()

    def getInterfaces(self):
        return (IMessageInfo,)
