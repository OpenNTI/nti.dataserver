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

from zope.security.interfaces import IPrincipal

from nti.app.messaging.utils import get_user

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IMessage
from nti.messaging.interfaces import IDeliveryService


@component.adapter(IMailbox, IMessage)
@interface.implementer(IDeliveryService)
class DefaultDeliveryService(object):

    def __init__(self, mailbox, message=None):
        self.mailbox = mailbox
        self.message = message

    def deliver(self, message=None):
        message = self.message if message is None else message
        for addressable in message.To or ():
            principal = IPrincipal(addressable)
            user = get_user(principal.id)
            if user is not None:
                mb = IMailbox(user)
                mb.receive(message)
            else:
                logger.warn("Cannot deliver message to %s", principal)
