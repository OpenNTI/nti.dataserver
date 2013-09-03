#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Chatserver functionality. This is all deprecated; prefer the nti.chatserver package.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import zope.deprecation
from zope.deprecation import deprecated

from nti.chatserver.interfaces import CHANNELS
from nti.chatserver.interfaces import CHANNEL_POLL
from nti.chatserver.interfaces import CHANNEL_META
from nti.chatserver.interfaces import CHANNEL_DEFAULT
from nti.chatserver.interfaces import CHANNEL_WHISPER
from nti.chatserver.interfaces import CHANNEL_CONTENT

# Many of these class names need to stick around to avoid broken objects
# in old datbases
zope.deprecation.__show__.off()

from nti.chatserver._handler import _ChatHandler
from nti.chatserver.messageinfo import MessageInfo
from nti.chatserver.meeting import _Meeting, _ModeratedMeeting

_ChatRoom = _Meeting
deprecated('_ChatRoom', 'Prefer _Meeting' )

_ModeratedChatRoom = _ModeratedMeeting
deprecated('_ModeratedChatRoom', 'Prefer _ModeratedMeeting' )

from nti.chatserver.chatserver import Chatserver
from nti.chatserver._handler import ChatHandlerFactory
from nti.chatserver.chatserver import PersistentMappingMeetingStorage

deprecated('Chatserver', 'Prefer nti.chatserver')
deprecated('MessageInfo', 'Prefer nti.chatserver')
deprecated('_ChatHandler', 'Prefer nti.chatserver')
deprecated('ChatHandlerFactory', 'Prefer nti.chatserver')
deprecated('PersistentMappingMeetingStorage', 'Prefer nti.chatserver')

zope.deprecation.__show__.on()
