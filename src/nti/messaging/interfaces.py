#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.container.constraints import contains

from zope.container.interfaces import IContainer

from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import IObjectEvent

from zope.location.interfaces import IContained

from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from zope.security.interfaces import IPrincipal

from nti.base.interfaces import ICreatedTime

from nti.coremetadata.interfaces import IUserGeneratedData
from nti.coremetadata.interfaces import IModeledContentBody

from nti.namedfile.interfaces import IFileConstrained

from nti.schema.field import Number
from nti.schema.field import Object
from nti.schema.field import TextLine
from nti.schema.field import ListOrTuple

from nti.threadable.interfaces import IThreadable

MSG_STATUS_VIEW = u'view'
MSG_STATUS_REPLY = u'reply'
MSG_STATUS_FORWARD = u'forward'

MSG_STATUS_VOCAB_BUCKETS = (
    MSG_STATUS_VIEW,
    MSG_STATUS_REPLY,
    MSG_STATUS_FORWARD
)

MSG_STATUS_VOCAB = SimpleVocabulary(
    [SimpleTerm(x) for x in MSG_STATUS_VOCAB_BUCKETS])


class IMessageBase(interface.Interface):

    Date = Number(title="UTC timestamp for the time the message is sent")

    From = Object(IPrincipal,
                  title="Addressable the message is from, author")

    To = ListOrTuple(title="Recipients",
                     value_type=Object(IPrincipal))

    Subject = TextLine(title="Subject of the message")


class IMessage(IMessageBase,
               IThreadable,
               ICreatedTime,
               IFileConstrained,
               IUserGeneratedData,
               IModeledContentBody):
    pass


class ISystemMessage(IMessage):
    pass


class IPeerToPeerMessage(IMessage):
    pass


class IReceivedMessage(IAttributeAnnotatable):

    ViewDate = Number(title="UTC timestamp when the message was viewed",
                      required=False)

    Message = Object(IMessage,
                     title="Reference to original message object owned by sender")

    ReplyDate = Number(title="UTC timestamp when the message was replied to",
                       required=False)

    def mark_viewed(time=None):
        """
        Marks this message as having been viewed.
        Emits an IReceivedMessageViewedEvent
        """

    def mark_replied_to(time=None):
        """
        Marks this message as having been replied to.
        Emits an IReceivedMessageRepliedToEvent
        """


class IReceivedMessageViewedEvent(IObjectEvent):
    """
    Fired when IReceivedMessage is replied to
    """
    ReceivedMessage = Object(IReceivedMessage,
                             title="The message that was replied to")


class IReceivedMessageRepliedToEvent(IObjectEvent):
    """
    Fired when IReceivedMessage is replied to
    """
    ReceivedMessage = Object(IReceivedMessage,
                             title="The message that was replied to")


class IReceivedMessageNotifier(interface.Interface):

    def notify(recv_msg):
        """
        Handle notification of the received message, e.g. an
        IReceivedMessage via e-mail, SMS, etc.
        """


class IDeliveryService(interface.Interface):

    def deliver(message):
        """
        Handle delivery of message (e.g. to its corresponding recipients)
        """


class IOwned(interface.Interface):
    """
    Something owned by an identified entity.  This may differ
    from ICreated['creator'] when, for example, an admin user
    creates something on behalf of a user
    """
    owner = interface.Attribute("The owner of this object.")
    owner.setTaggedValue('_ext_excluded_out', True)


class IMessageContainer(IContainer):
    """
    A container for all IMessages.
    """
    contains(IMessage)
    __setitem__.__doc__ = None

    def append_message(message):
        """
        Add the provided message into this container.
        """
    add = append = append_message

    def get_message(ntiid):
        """
        Get the message with given ntiid.
        """

    def delete_message(message):
        """
        Remove the provided message from the container
        """
    remove = delete = delete_message


class IReceivedMessageContainer(IContainer):
    """
    A container for all IReceivedMessages.
    """
    contains(IReceivedMessage)
    __setitem__.__doc__ = None

    def append_message(message):
        """
        Add the provided message into this container.
        """
    add = append = append_message

    def get_message(ntiid):
        """
        Get the message with given ntiid.
        """

    def delete_message(message):
        """
        Remove the provided message from the container
        """
    remove = delete = append_message


class IMailbox(IOwned, IContained):

    Sent = Object(IMessageContainer,
                  title='Sent messages')
    Sent.setTaggedValue('_ext_excluded_out', True)

    Received = Object(IReceivedMessageContainer,
                      title='Received messages')
    Received.setTaggedValue('_ext_excluded_out', True)

    def send(message):
        """
        Handle storage of sent message
        """

    def receive(message):
        """
        Handle storage of received message
        """


@interface.implementer(IReceivedMessageViewedEvent)
class ReceivedMessageViewedEvent(ObjectEvent):

    @property
    def ReceivedMessage(self):
        return self.object
    message = ReceivedMessage


@interface.implementer(IReceivedMessageRepliedToEvent)
class RecievedMessageRepliedToEvent(ObjectEvent):

    @property
    def ReceivedMessage(self):
        return self.object
    message = ReceivedMessage
