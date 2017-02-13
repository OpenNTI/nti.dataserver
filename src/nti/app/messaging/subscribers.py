#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.app.messaging.utils import get_user

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IDeliveryService
from nti.messaging.interfaces import IReceivedMessageNotifier


def message_added(message, event):
    from_ = get_user(message.From)
    sender_mailbox = component.queryMultiAdapter((from_, message), IMailbox)
    if sender_mailbox is None:
        logger.warn("Cannot find sender mailfor for %s", message.From)
    else:
        deliverers = component.subscribers((message, sender_mailbox),
                                           IDeliveryService)
        for delivery_service in deliverers or ():
            delivery_service.deliver(message)


def recv_message_added(recv_msg, event):
    recipient_mailbox = IMailbox(recv_msg, None)
    notifiers = component.subscribers((recv_msg.Message, recipient_mailbox),
                                      IReceivedMessageNotifier)
    for notifier in notifiers:
        notifier.notify(recv_msg)
