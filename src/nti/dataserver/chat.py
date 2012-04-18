""" Chatserver functionality. This is all deprecated; prefer the nti.chatserver package."""

__docformat__ = "restructuredtext en"

from zope.deprecation import deprecated


from nti.chatserver.interfaces import CHANNELS, CHANNEL_DEFAULT, CHANNEL_WHISPER, CHANNEL_CONTENT, CHANNEL_POLL, CHANNEL_META


from nti.chatserver.messageinfo import MessageInfo
from nti.chatserver.meeting import _Meeting, _ModeratedMeeting
from nti.chatserver._handler import _ChatHandler

_ChatRoom = _Meeting
deprecated('_ChatRoom', 'Prefer _Meeting' )


_ModeratedChatRoom = _ModeratedMeeting
deprecated('_ModeratedChatRoom', 'Prefer _ModeratedMeeting' )

from nti.chatserver._handler import ChatHandlerFactory
from nti.chatserver.chatserver import PersistentMappingMeetingStorage, Chatserver

deprecated( 'ChatHandlerFactory', 'Prefer nti.chatserver' )
deprecated( '_ChatHandler', 'Prefer nti.chatserver' )
deprecated( 'MessageInfo', 'Prefer nti.chatserver' )
deprecated( 'Chatserver', 'Prefer nti.chatserver' )
deprecated( 'PersistentMappingMeetingStorage', 'Prefer nti.chatserver' )
