#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

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

zope.deferredimport.deprecated(
    "Import from nti.chatserver.meeting._Meeting instead",
    _ChatRoom='nti.chatserver.meeting:_Meeting')

zope.deferredimport.deprecated(
    "Import from nti.chatserver.meeting._Meeting instead",
    _ModeratedChatRoom='nti.chatserver.meeting:_Meeting')

import zope.deprecation
from zope.deprecation import deprecated

# Many of these class names need to stick around to avoid broken objects
# in old datbases
zope.deprecation.__show__.off()

deprecated('Chatserver', 'Prefer nti.chatserver')
deprecated('MessageInfo', 'Prefer nti.chatserver')
deprecated('_ChatHandler', 'Prefer nti.chatserver')
deprecated('ChatHandlerFactory', 'Prefer nti.chatserver')
deprecated('PersistentMappingMeetingStorage', 'Prefer nti.chatserver')

zope.deprecation.__show__.on()
