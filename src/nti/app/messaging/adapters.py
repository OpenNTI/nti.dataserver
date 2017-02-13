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

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import ISystemUserPrincipal

from nti.dataserver.interfaces import SYSTEM_USER_ID

from nti.dataserver.users import User

from nti.messaging import SYSTEM_MAILBOX_KEY

from nti.messaging.adapters import mailbox_for_annotable
from nti.messaging.adapters import message_for_mailbox_received_message

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IMessage
from nti.messaging.interfaces import IReceivedMessage

from nti.messaging.storage import Mailbox


@component.adapter(IUser)
@component.adapter(IUser, IMessage)
@interface.implementer(IMailbox)
def mailbox_for_user(user, message=None):
    return mailbox_for_annotable(user, create=True)


def _dataserver_folder():
    dataserver = component.getUtility(IDataserver)
    return IShardLayout(dataserver).dataserver_folder


def system_user_mailbox():
    folder = _dataserver_folder()
    try:
        result = folder[SYSTEM_MAILBOX_KEY]
    except KeyError:
        result = Mailbox()
        folder[SYSTEM_MAILBOX_KEY] = result
        result.creator = SYSTEM_USER_ID
    return result


@interface.implementer(IMailbox)
@component.adapter(IPrincipal, IMessage)
def principal_mailbox(principal, message):
    if ISystemUserPrincipal.providedBy(principal):
        return system_user_mailbox()
    else:
        user = User.get_user(principal.id)
        return mailbox_for_annotable(user) if user else None


@component.adapter(IUser, IMessage)
@interface.implementer(IReceivedMessage)
def message_for_user_received_message(user, message):
    mailbox = IMailbox(user, None)
    if mailbox is not None:
        return message_for_mailbox_received_message(mailbox, message)
    return None
