#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Listeners for socket activity.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.event import notify

from nti.chatserver.interfaces import IContacts
from nti.chatserver.interfaces import PresenceChangedUserNotificationEvent
from nti.chatserver.interfaces import IContactISubscribeToAddedToContactsEvent

from nti.dataserver import users
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver

from nti.socketio.interfaces import ISocketSession
from nti.socketio.interfaces import ISocketSessionDisconnectedEvent

def _is_user_online(dataserver, username, ignoring_session=None):
	"""
	:return: A value that can be used as a boolean saying the user is online. In reality,
		it will be an iterable of the user's sessions.
	"""
	try:
		sessions = set(dataserver.sessions.get_sessions_by_owner(username))
	except KeyError:  # Hmm. session_storage.py reports some inconsistency errors sometimes. Which is bad
		logger.exception("Failed to get all sessions for owner %s", username)
		sessions = set()

	if ignoring_session:
		sessions.discard(ignoring_session)
	return sessions

def _notify_friends_of_presence(session, presence, event=None):
	user = users.User.get_user(session.owner) if session else None
	if user is None:
		logger.error("Unable to get owner of session %s; not sending presence notification", session)
		return

	has_me_in_buddy_list = IContacts(user).contactNamesSubscribedToMyPresenceUpdates
	logger.debug("Notifying %s of presence change of %s/%s to %s for %s",
				 has_me_in_buddy_list, session.owner, session, presence, event)
	notify(PresenceChangedUserNotificationEvent(has_me_in_buddy_list, session.owner, presence))

@component.adapter(ISocketSession, ISocketSessionDisconnectedEvent)
def session_disconnected_broadcaster(session, event):
	# TODO: Should this all move to a lower level? Or is the "application"
	# level the right one for this?
	dataserver = component.queryUtility(IDataserver)
	if not (dataserver and dataserver.sessions):
		logger.debug("Unable to broadcast presence notification.")
		return

	online = _is_user_online(dataserver, session.owner, session)
	if not online:
		# Send notifications to contacts by default...
		need_notify = True
		cs = dataserver.chatserver
		if cs:
			# ... however, if the protocol has been followed properly,
			# we may not need to. If it hasn't and they didn't set a valid presence,
			# then we need to do that too.
			presences = cs.getPresenceOfUsers([session.owner])
			# This will return an empty array if the user is "default" unavailable
			# Don't change that. If they left an available presence, go back
			# to a default presence.
			if presences and presences[0].isAvailable():
				cs.removePresenceOfUser(session.owner)
				# Broadcast the default unavailable presence because they clearly
				# neglected to do so
				need_notify = True
			elif presences and not presences[0].isAvailable():
				# Yay! He was a good boy and set a presence. This
				# would already have been broadcast
				need_notify = False
			elif not presences:
				# Hmm. No presence info at all. Weird.
				# Make sure to notify anyway.
				need_notify = True

		if need_notify:
			_notify_friends_of_presence(session, PresenceChangedUserNotificationEvent.P_OFFLINE, event)
	else:
		logger.debug("A session (%s) died, but %s are still online", session, len(online))

@component.adapter(IUser, IContactISubscribeToAddedToContactsEvent)
def send_presence_when_contact_added(user_now_following, event):
	"""
	When I add a contact that I want to subscribe to, send
	his presence info, if we can.

	"""
	user_being_followed = event.contact
	if user_being_followed is None or user_now_following is None:  # pragma: no cover
		return

	dataserver = component.queryUtility(IDataserver)
	if not (dataserver and dataserver.sessions and dataserver.chatserver):
		return

	if not _is_user_online(dataserver, user_now_following):
		return

	sessions = _is_user_online(dataserver, user_being_followed)
	if sessions:
		cs = dataserver.chatserver
		# Yes, we are online, but are we available?
		session = next(iter(sessions))
		presences = cs.getPresenceOfUsers([session.owner])
		# This will return an empty array if the user is "default" unavailable
		if presences and presences[0].isAvailable():
			# TODO: Losing 'status' information here
			_notify_friends_of_presence(session, PresenceChangedUserNotificationEvent.P_ONLINE, event)
