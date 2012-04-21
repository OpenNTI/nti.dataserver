#!/usr/bin/env python2.7

"""
Listeners for socket activity.
"""

import logging
logger = logging.getLogger(__name__)

from nti.dataserver import interfaces as nti_interfaces, users
from nti.chatserver import interfaces as chat_interfaces
from nti.socketio import interfaces as sio_interfaces
from zope import component

def _is_user_online(dataserver, username, ignoring_session=None):
	"""
	:return: A value that can be used as a boolean saying the user is online. In reality,
		it will be an iterable of the user's sessions.
	"""
	sessions = set(dataserver.sessions.get_sessions_by_owner(username))
	if ignoring_session: sessions.discard( ignoring_session )
	return sessions

def _notify_friends_of_presence( session, presence, dataserver=None ):
	dataserver = dataserver or component.queryUtility( nti_interfaces.IDataserver )
	chatserver = component.queryUtility( chat_interfaces.IChatserver )
	if dataserver is None or chatserver is None:
		logger.debug( "Unable to broadcast presence notification. DS: %s CS %s", dataserver, chatserver )
		return

	has_me_in_buddy_list = ()
	user = users.User.get_user( session.owner, dataserver=dataserver )
	if user is None:
		logger.error( "Unable to get owner of session %s; not sending presence notification", session )
		return

	# TODO: Better algorithm. Who should this really go to?
	has_me_in_buddy_list = user.following | set(user._sources_accepted)
	logger.debug( "Notifying %s of presence change of %s to %s", has_me_in_buddy_list, session.owner, presence )
	chatserver.notify_presence_change( session.owner, presence, has_me_in_buddy_list )

@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionDisconnectedEvent )
def session_disconnected_broadcaster( session, event ):
	dataserver = component.queryUtility( nti_interfaces.IDataserver )
	if not (dataserver and dataserver.sessions):
		logger.debug( "Unable to broadcast presence notification.")
		return

	online = _is_user_online( dataserver, session.owner, session )
	if not online:
		_notify_friends_of_presence( session, 'Offline' )
	else:
		logger.debug( "A session (%s) died, but some are still online (%s)", session, online )


@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionConnectedEvent )
def session_connected_broadcaster( session, event ):
	_notify_friends_of_presence( session, 'Online' )

## Add presence info to users


def _UserPresenceExternalDecoratorFactory( user ):
	# TODO: Presence information will depend on who's asking
	ds = component.queryUtility( nti_interfaces.IDataserver )
	if user and ds and ds.sessions:
		return _UserPresenceExternalDecorator( user, ds )

class _UserPresenceExternalDecorator(object):
	def __init__( self, user, ds ):
		self.ds = ds

	def decorateExternalObject( self, user, result ):
		result['Presence'] =  "Online" if _is_user_online( self.ds, user.username ) else "Offline"
