#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope import interface

from zope.annotation.interfaces import IAnnotations
from zope.annotation.interfaces import IAttributeAnnotatable

from zope.security.interfaces import IPrincipal

from ZODB.interfaces import IConnection

from nti.messaging import MAILBOX_ANNOTATION_KEY

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IMessage
from nti.messaging.interfaces import IReceivedMessage
from nti.messaging.interfaces import IReceivedMessageContainer

from nti.messaging.model import ReceivedMessage

from nti.messaging.storage import Mailbox


@interface.implementer(IMailbox)
@component.adapter(IAttributeAnnotatable)
def mailbox_for_annotable(annotable, create=True):
    mailbox = None
    annotations = IAnnotations(annotable)
    connection = IConnection(annotable, None)
    try:
        mailbox = annotations[MAILBOX_ANNOTATION_KEY]
    except KeyError:
        if create:
            mailbox = Mailbox()
            if connection is not None:
                connection.add(mailbox)
            annotations[MAILBOX_ANNOTATION_KEY] = mailbox
            mailbox.__parent__ = annotable
            mailbox.__name__ = MAILBOX_ANNOTATION_KEY
    return mailbox


@interface.implementer(IMailbox)
@component.adapter(IReceivedMessage)
def mailbox_for_received_message(received_message):
    container = IReceivedMessageContainer(received_message, None)
    return container.__parent__ if container else None


@component.adapter(IMailbox, IMessage)
@interface.implementer(IReceivedMessage)
def message_for_mailbox_received_message(mailbox, message):
    return mailbox.Received.get(message.__name__)


@component.adapter(IReceivedMessage)
@interface.implementer(IReceivedMessageContainer)
def received_messages(received_message):
    return received_message.__parent__ if received_message else None


@component.adapter(IMessage)
@interface.implementer(IReceivedMessage)
def received_message_factory(message):
    if message is not None:
        return ReceivedMessage(Message=message)
    return None


@interface.implementer(IPrincipal)
@component.adapter(IReceivedMessage)
def message_owner(received_message):
    return IPrincipal(IMailbox(received_message).__parent__, None)
