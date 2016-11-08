#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Chatserver functionality. This is all deprecated; prefer the nti.chatserver package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.chatserver.interfaces",
    "nti.chatserver.interfaces",
    "CHANNELS",
    "CHANNEL_POLL",
    "CHANNEL_META",
    "CHANNEL_DEFAULT",
    "CHANNEL_WHISPER",
    "CHANNEL_CONTENT")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.chatserver._handler",
    "nti.chatserver._handler",
    "_ChatHandler",
    "ChatHandlerFactory")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.chatserver.messageinfo",
    "nti.chatserver.messageinfo",
    "MessageInfo")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.chatserver.chatserver",
    "nti.chatserver.chatserver",
    "Chatserver")

import zope.deprecation
from zope.deprecation import deprecated

# Many of these class names need to stick around to avoid broken objects
# in old datbases
zope.deprecation.__show__.off()

from nti.chatserver.meeting import _Meeting, _ModeratedMeeting

_ChatRoom = _Meeting
deprecated('_ChatRoom', 'Prefer _Meeting' )

_ModeratedChatRoom = _ModeratedMeeting
deprecated('_ModeratedChatRoom', 'Prefer _ModeratedMeeting' )

deprecated('Chatserver', 'Prefer nti.chatserver')
deprecated('MessageInfo', 'Prefer nti.chatserver')
deprecated('_ChatHandler', 'Prefer nti.chatserver')
deprecated('ChatHandlerFactory', 'Prefer nti.chatserver')
deprecated('PersistentMappingMeetingStorage', 'Prefer nti.chatserver')

zope.deprecation.__show__.on()
