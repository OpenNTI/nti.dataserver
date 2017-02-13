#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import lifecycleevent

from zope.cachedescriptors.property import readproperty

from zope.container.contained import Contained

from zope.location import locate

from ZODB.interfaces import IConnection

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IReceivedMessage
from nti.messaging.interfaces import IMessageContainer
from nti.messaging.interfaces import IReceivedMessageContainer


def save_in_container(container, key, value, event=True):
    if event:
        container[key] = value
    else:
        # avoid dublincore annotations for performance
        container._setitemf(key, value)
        locate(value, parent=container, name=key)
        if      IConnection(container, None) is not None \
            and IConnection(value, None) is None:
            IConnection(container).add(value)
        lifecycleevent.added(value, container, key)
        try:
            container.updateLastMod()
        except AttributeError:
            pass
        container._p_changed = True
    return value


class MessageContainerBase(CaseInsensitiveCheckingLastModifiedBTreeContainer,
                           Contained):

    def __init__(self):
        CaseInsensitiveCheckingLastModifiedBTreeContainer.__init__(self)
        
    def _build_key(self):
        return self.generateId("msg_")

    @property
    def creator(self):
        return self.__parent__.creator
    owner = creator

    def get_message(self, mid):
        return self[mid]

    def append_message(self, message, event=False):
        key = message.__name__ or self._build_key()
        return save_in_container(self, key, message, event=event)
    add = append_message

    def delete_message(self, message):
        del self[message.__name__]
    delete = delete_message


@interface.implementer(IReceivedMessageContainer)
class ReceivedMessageContainer(MessageContainerBase):

    def _build_key(self):
        return self.generateId("recv_msg_")


@interface.implementer(IMessageContainer)
class MessageContainer(MessageContainerBase):
    pass

@interface.implementer(IMailbox)
class Mailbox(CaseInsensitiveCheckingLastModifiedBTreeContainer,
              Contained):

    __external_can_create__ = False
    __external_class_name__ = 'Mailbox'

    mimeType = mime_type = 'application/vnd.nextthought.messaging.mailbox'

    def __init__(self):
        super(Mailbox, self).__init__()

    def reset(self):
        self.Sent = self['Sent'] = MessageContainer()
        self.Received = self['Received'] = ReceivedMessageContainer()

    @readproperty
    def creator(self):
        return self.__parent__
    owner = creator

    def send(self, message):
        if not message.creator:
            message.creator = message.From.id  # principal id
        self.Sent.append_message(message)

    def receive(self, message):
        received_message = IReceivedMessage(message)
        return self.Received.append_message(received_message)

    def get_received(self):
        return self.Received

    def get_sent(self):
        return self.Sent

    @property
    def lastModified(self):
        return max(self.Sent.lastModified, self.Received.lastModified)
    last_modified = lastModified
