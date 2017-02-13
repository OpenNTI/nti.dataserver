#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time as tm

from zope import interface
from zope import lifecycleevent

from zope.event import notify

from zope.container.contained import Contained

from zope.schema.fieldproperty import FieldProperty
from zope.schema.fieldproperty import createFieldProperties

from nti.coremetadata.schema import BodyFieldProperty

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.messaging.interfaces import IMessage
from nti.messaging.interfaces import IMessageBase
from nti.messaging.interfaces import ISystemMessage
from nti.messaging.interfaces import IReceivedMessage
from nti.messaging.interfaces import IPeerToPeerMessage

from nti.messaging.interfaces import ReceivedMessageViewedEvent
from nti.messaging.interfaces import RecievedMessageRepliedToEvent

from nti.property.property import alias

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import PermissiveSchemaConfigured as SchemaConfigured

from nti.threadable.threadable import Threadable as ThreadableMixin


@interface.implementer(IMessage)
class Message(ThreadableMixin,
              SchemaConfigured,
              PersistentCreatedModDateTrackingObject,
              Contained):

    __external_can_create__ = False
    __external_class_name__ = 'Message'

    mimeType = mime_type = 'application/vnd.nextthought.messaging.message'

    createDirectFieldProperties(IMessageBase)
    createDirectFieldProperties(IMessage, omit=('Date',))

    body = BodyFieldProperty(IMessage['body'])

    title = FieldProperty(IMessage['title'])

    id = alias('__name__')

    containerId = None

    Date = alias('createdTime')

    def __init__(self, *args, **kwargs):
        ThreadableMixin.__init__(self)
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(IPeerToPeerMessage)
class PeerToPeerMessage(Message):
    createDirectFieldProperties(IPeerToPeerMessage)

    __external_can_create__ = True
    __external_class_name__ = 'PeerToPeerMessage'

    mimeType = mime_type = 'application/vnd.nextthought.messaging.peertopeermessage'


@interface.implementer(ISystemMessage)
class SystemMessage(Message):
    createDirectFieldProperties(ISystemMessage)

    __external_can_create__ = False
    __external_class_name__ = 'SystemMessage'

    mimeType = mime_type = 'application/vnd.nextthought.messaging.systemmessage'


@interface.implementer(IReceivedMessage)
class ReceivedMessage(SchemaConfigured,
                      PersistentCreatedModDateTrackingObject,
                      Contained):

    createFieldProperties(IReceivedMessage)

    __external_class_name__ = 'ReceivedMessage'

    mimeType = mime_type = 'application/vnd.nextthought.messaging.receivedmessage'

    id = alias('__name__')
    message = alias('Message')

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

    def mark_forwarded(self, time=None):
        time = tm.time() if time is None else time
        self.ForwardDate = time
        lifecycleevent.modified(self)

    def mark_viewed(self, time=None, should_notify=True, force=False):
        if self.ViewDate and not force:
            return
        time = tm.time() if time is None else time
        self.ViewDate = time
        if should_notify:
            notify(ReceivedMessageViewedEvent(self))
        lifecycleevent.modified(self)

    def mark_replied_to(self, time=None, should_notify=True, force=False):
        if self.ReplyDate and not force:
            return
        time = tm.time() if time is None else time
        self.ReplyDate = time
        if should_notify:
            notify(RecievedMessageRepliedToEvent(self))
        lifecycleevent.modified(self)

    def __setattr__(self, name, value):
        if name.lower() == 'message' and value is not None:
            super(ReceivedMessage, self).__setattr__('id', value.id)
        PersistentCreatedModDateTrackingObject.__setattr__(self, name, value)
