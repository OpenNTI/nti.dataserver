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
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

from zope.event import notify
from zope import component
from zope import interface

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

	has_me_in_buddy_list = chat_interfaces.IContacts(user).contactNamesSubscribedToMyPresenceUpdates
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
		# If they didn't set a valid presence, then we need to do that too.
		# TODO: This will move when this legacy stuff goes away too
		cs = dataserver.chatserver
		if cs:
			presences = cs.getPresenceOfUsers( [session.owner] )
			# This will return an empty array if the user is "default" unavailable
			# (Which we expect to be the initial case in the near future). Don't
			# change that. If they left an available presence, go back
			# to a default presence.
			# TODO: Somebody needs to broadcast the new presence event (presenceOfUsersChanged).
			# Not doing it now to prevent warnings in the app console until they can
			# handle the event
			if presences and presences[0].isAvailable():
				cs.removePresenceOfUser( session.owner )
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

@component.adapter(nti_interfaces.IUser)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _UserPresenceExternalDecorator(object):
	__metaclass__ = SingletonDecorator

	def decorateExternalObject( self, user, result ):
		# TODO: Presence information will depend on who's asking
		ds = component.queryUtility( nti_interfaces.IDataserver )
		if user and ds and ds.sessions:
			result['Presence'] =  "Online" if _is_user_online( ds, user.username ) else "Offline"
