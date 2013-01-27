#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Listeners for socket activity.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from nti.dataserver import interfaces as nti_interfaces, users
from nti.chatserver import interfaces as chat_interfaces
from nti.socketio import interfaces as sio_interfaces
from zope.event import notify
from zope import component

def _is_user_online(dataserver, username, ignoring_session=None):
	"""
	:return: A value that can be used as a boolean saying the user is online. In reality,
		it will be an iterable of the user's sessions.
	"""
	try:
		sessions = set(dataserver.sessions.get_sessions_by_owner(username))
	except KeyError: # Hmm. session_storage.py reports some inconsistency errors sometimes. Which is bad
		logger.exception( "Failed to get all sessions for owner %s", username )
		sessions = set()

	if ignoring_session:
		sessions.discard( ignoring_session )
	return sessions

def _notify_friends_of_presence( session, presence, event=None ):
	user = users.User.get_user( session.owner ) if session else None
	if user is None:
		logger.error( "Unable to get owner of session %s; not sending presence notification", session )
		return

	# TODO: Better algorithm. Who should this really go to?
	has_me_in_buddy_list = {e.username for e in user.entities_followed} | set(user.accepting_shared_data_from)
	logger.debug( "Notifying %s of presence change of %s/%s to %s for %s", has_me_in_buddy_list, session.owner, session, presence, event )
	notify( chat_interfaces.PresenceChangedUserNotificationEvent( has_me_in_buddy_list, session.owner, presence ) )


@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionDisconnectedEvent )
def session_disconnected_broadcaster( session, event ):
	dataserver = component.queryUtility( nti_interfaces.IDataserver )
	if not (dataserver and dataserver.sessions):
		logger.debug( "Unable to broadcast presence notification.")
		return

	online = _is_user_online( dataserver, session.owner, session )
	if not online:
		_notify_friends_of_presence( session, chat_interfaces.PresenceChangedUserNotificationEvent.P_OFFLINE, event )
	else:
		logger.debug( "A session (%s) died, but %s are still online", session, len(online) )


@component.adapter( sio_interfaces.ISocketSession, sio_interfaces.ISocketSessionConnectedEvent )
def session_connected_broadcaster( session, event ):
	_notify_friends_of_presence( session, chat_interfaces.PresenceChangedUserNotificationEvent.P_ONLINE, event )

## Add presence info to users during externalization
## FIXME: This information is transient and so by doing this
## we invalidate any 'Last Modified' information we're sending at a higher level,
## (since that's based on the static info) and so this makes
## certain things that might be cached unreliable in the web app.
## We've added a workaround for FriendsLists specifically, but
## it was probably a design mistake to mix the static and dynamic info, and
## we need separate URLs to correct that.

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
