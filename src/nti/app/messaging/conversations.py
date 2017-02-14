#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from itertools import chain

from zope import component
from zope import interface

from nti.app.authentication import get_remote_user

from nti.app.messaging.interfaces import IConversation
from nti.app.messaging.interfaces import IConversationProvider

from nti.dataserver import authorization as nauth

from nti.dataserver.authorization_acl import has_permission

from nti.dataserver.interfaces import IThreadable

from nti.messaging.interfaces import IMailbox
from nti.messaging.interfaces import IReceivedMessage

from nti.schema.fieldproperty import createDirectFieldProperties


def is_top_level(item):
    return not IThreadable.providedBy(item) or not item.inReplyTo


@interface.implementer(IConversation)
class Conversation(object):
    createDirectFieldProperties(IConversation)

    __external_can_create__ = False

    mimeType = mime_type = 'application/vnd.nextthought.messaging.conversation'

    def __init__(self, mailbox, root, messages=(), user=None):
        self._reset(mailbox, root, messages, user)

    def _reset(self, mailbox, root, messages=(), user=None):
        most_recent = None
        unopened_count = 0
        participants = set()
        remote_user = user or get_remote_user()
        for message in messages or ():
            if not has_permission(nauth.ACT_READ, message, remote_user):
                continue
            if not most_recent or most_recent.createdTime < message.createdTime:
                most_recent = message
            participants.add(message.From)
            participants.update(message.To)
            recv_msg = component.queryMultiAdapter((mailbox, message),
                                                   IReceivedMessage)
            if recv_msg is None or recv_msg.ViewDate is None:
                unopened_count += 1

        self.RootMessage = root
        self.UnOpenedCount = unopened_count
        self.MostRecentMessage = most_recent
        self.Participants = tuple(participants)


@component.adapter(IMailbox)
@interface.implementer(IConversationProvider)
class ConversationProvider(object):

    def __init__(self, mailbox):
        self.mailbox = mailbox

    def conversation_for_toplevel(self, root, user=None):
        return Conversation(root,
                            self.mailbox,
                            chain(root.referents, (root,)),
                            user=user)

    def conversations(self, user=None):
        """
        Identify conversations in the provided mailbox. Each unique thread
        is a conversation.
        """

        toplevels = [x for x in self.mailbox.Sent.values() if is_top_level(x)]

        # received needs unwrapped
        for received in self.mailbox.Received.values():
            msg = received.Message
            if not is_top_level(msg):
                # it is a reply. Make sure the top level portion of this
                # thread is in toplevels. for p2p conversations this will be
                # true already.  for things replied to a system message we
                # may have to go look it up.
                msg = msg.references[-1]

            if msg not in toplevels:
                toplevels.append(msg)

        # Each top level thing is a conversation
        return tuple(self.conversation_for_toplevel(x, user) for x in toplevels)
